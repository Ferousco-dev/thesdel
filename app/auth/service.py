import uuid
from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.repository import AuthTokenRepository, SessionRepository, UserRepository
from app.auth.schemas import TokenPairResponse, UserPublic
from app.shared.config import Settings
from app.shared.errors import (
    ConflictError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.shared.jobs import enqueue_email_verification, enqueue_password_reset_email
from app.shared.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_google_id_token,
    verify_password,
)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings) -> None:
        self._users = UserRepository(db)
        self._sessions = SessionRepository(db)
        self._auth_tokens = AuthTokenRepository(db)
        self._settings = settings

    async def register(
        self, *, email: str, password: str, display_name: str, device_label: str | None = None
    ) -> tuple[TokenPairResponse, UserPublic]:
        existing = await self._users.find_by_email(email)
        if existing is not None:
            # Deliberately generic — do not reveal that this email is taken
            # via a distinct error, per docs/SECURITY.md §2 enumeration guidance.
            # Registration is the one place a slightly more specific message
            # is acceptable since the user just typed the email themselves.
            raise ConflictError("An account with this email already exists.")

        user = await self._users.create(
            email=email, password_hash=hash_password(password), display_name=display_name
        )
        tokens = await self._issue_token_pair(
            user_id=str(user["_id"]), tier=user["tier"], device_label=device_label
        )
        # Signup itself is never blocked on verification (docs/SECURITY.md)
        # — the token is issued and the email enqueued, but a Redis/queue
        # hiccup here must not fail the registration response, which is
        # handled by enqueue_email_verification's own swallow-and-log.
        await self._issue_verification_token(user_id=str(user["_id"]), email=user["email"])
        return tokens, _to_public(user)

    async def login(
        self, *, email: str, password: str, device_label: str | None = None
    ) -> tuple[TokenPairResponse, UserPublic]:
        user = await self._users.find_by_email(email)
        # A Google-only account has password_hash=None — reject rather than
        # let verify_password blow up on a missing hash.
        if user is None or user["password_hash"] is None or not verify_password(
            password, user["password_hash"]
        ):
            raise InvalidCredentialsError()

        tokens = await self._issue_token_pair(
            user_id=str(user["_id"]), tier=user["tier"], device_label=device_label
        )
        return tokens, _to_public(user)

    async def google_login(
        self, *, id_token: str, device_label: str | None = None
    ) -> tuple[TokenPairResponse, UserPublic]:
        """See docs/DECISIONS.md ADR-011. Finds an account by Google's
        stable `sub` claim first; if none exists but the verified email
        matches an existing password account, links Google to it instead
        of creating a duplicate. Only auto-links when Google itself
        reports the email as verified — otherwise someone who merely
        registered a Google account with an unverified alias of another
        person's email could hijack that account."""
        claims = verify_google_id_token(id_token)
        google_id = claims["sub"]
        email = claims["email"]
        email_verified = bool(claims.get("email_verified", False))
        display_name = claims.get("name") or email.split("@")[0]

        user = await self._users.find_by_google_id(google_id)
        if user is None:
            existing = await self._users.find_by_email(email)
            if existing is not None:
                if not email_verified:
                    raise InvalidCredentialsError(
                        "Google did not confirm this email is verified."
                    )
                await self._users.link_google_id(existing["_id"], google_id)
                user = await self._users.find_by_id(str(existing["_id"]))
            else:
                user = await self._users.create(
                    email=email,
                    display_name=display_name,
                    google_id=google_id,
                    email_verified=email_verified,
                )

        tokens = await self._issue_token_pair(
            user_id=str(user["_id"]), tier=user["tier"], device_label=device_label
        )
        return tokens, _to_public(user)

    async def refresh(self, refresh_token: str) -> TokenPairResponse:
        token_hash = hash_opaque_token(refresh_token)
        session = await self._sessions.find_by_token_hash(token_hash)

        if session is None:
            raise TokenInvalidError()

        if session["revoked_at"] is not None:
            # Reuse of an already-rotated-away token — theft signal.
            # Revoke the entire family, per docs/SECURITY.md threat table.
            await self._sessions.revoke_family(session["family_id"])
            raise TokenInvalidError()

        expires_at = session["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise TokenInvalidError()

        user = await self._users.find_by_id(str(session["user_id"]))
        if user is None:
            raise TokenInvalidError()

        await self._sessions.revoke(session["_id"])

        return await self._issue_token_pair(
            user_id=str(user["_id"]),
            tier=user["tier"],
            device_label=session.get("device_label"),
            family_id=session["family_id"],
        )

    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_opaque_token(refresh_token)
        session = await self._sessions.find_by_token_hash(token_hash)
        if session is not None and session["revoked_at"] is None:
            await self._sessions.revoke(session["_id"])

    async def _issue_token_pair(
        self,
        *,
        user_id: str,
        tier: str,
        device_label: str | None,
        family_id: str | None = None,
    ) -> TokenPairResponse:
        access_token = create_access_token(user_id=user_id, tier=tier)

        refresh_token = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days)

        await self._sessions.create(
            user_id=user_id,
            refresh_token_hash=hash_opaque_token(refresh_token),
            expires_at=expires_at,
            device_label=device_label,
            family_id=family_id or uuid.uuid4().hex,
        )

        return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)

    async def _issue_verification_token(self, *, user_id: str, email: str) -> None:
        token = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self._settings.email_verification_ttl_minutes
        )
        await self._auth_tokens.create(
            user_id=user_id,
            purpose="email_verification",
            token_hash=hash_opaque_token(token),
            expires_at=expires_at,
        )
        await enqueue_email_verification(user_id=user_id, email=email, token=token)

    async def resend_verification(self, email: str) -> None:
        """Always a no-op-looking success at the router layer (enumeration-
        safe) — only actually issues a token when the account exists and
        isn't already verified."""
        user = await self._users.find_by_email(email)
        if user is not None and user["email_verified_at"] is None:
            await self._issue_verification_token(user_id=str(user["_id"]), email=user["email"])

    async def verify_email(self, token: str) -> None:
        token_hash = hash_opaque_token(token)
        record = await self._auth_tokens.find_by_hash(token_hash)
        if record is None or record["purpose"] != "email_verification":
            raise TokenInvalidError()

        if record["used_at"] is not None:
            # Idempotent-success if this exact token already verified the
            # account; otherwise it's a genuinely reused/invalidated token.
            user = await self._users.find_by_id(str(record["user_id"]))
            if user is not None and user["email_verified_at"] is not None:
                return
            raise TokenInvalidError()

        if _aware(record["expires_at"]) < datetime.now(UTC):
            raise TokenExpiredError()

        await self._auth_tokens.mark_used(record["_id"])
        await self._users.mark_email_verified(str(record["user_id"]))

    async def request_password_reset(self, email: str) -> None:
        """Always returns (via the router) a generic success response
        regardless of whether the email exists — mirrors login/register's
        enumeration-safe pattern, per docs/SECURITY.md §2."""
        user = await self._users.find_by_email(email)
        if user is None:
            return

        token = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self._settings.password_reset_ttl_minutes
        )
        await self._auth_tokens.create(
            user_id=str(user["_id"]),
            purpose="password_reset",
            token_hash=hash_opaque_token(token),
            expires_at=expires_at,
        )
        await enqueue_password_reset_email(
            user_id=str(user["_id"]), email=user["email"], token=token
        )

    async def confirm_password_reset(self, *, token: str, new_password: str) -> None:
        token_hash = hash_opaque_token(token)
        record = await self._auth_tokens.find_by_hash(token_hash)
        if record is None or record["purpose"] != "password_reset" or record["used_at"] is not None:
            raise TokenInvalidError()

        if _aware(record["expires_at"]) < datetime.now(UTC):
            raise TokenExpiredError()

        user_id = str(record["user_id"])
        await self._auth_tokens.mark_used(record["_id"])
        await self._users.update_password_hash(user_id, hash_password(new_password))
        # Force re-login everywhere — a password reset must invalidate every
        # existing session, not just the one that requested the reset.
        await self._sessions.revoke_all_for_user(user_id)


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        display_name=user["display_name"],
        tier=user["tier"],
    )
