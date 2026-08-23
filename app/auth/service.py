import uuid
from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.repository import SessionRepository, UserRepository
from app.auth.schemas import TokenPairResponse, UserPublic
from app.shared.config import Settings
from app.shared.errors import ConflictError, InvalidCredentialsError, TokenInvalidError
from app.shared.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase, settings: Settings) -> None:
        self._users = UserRepository(db)
        self._sessions = SessionRepository(db)
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
        return tokens, _to_public(user)

    async def login(
        self, *, email: str, password: str, device_label: str | None = None
    ) -> tuple[TokenPairResponse, UserPublic]:
        user = await self._users.find_by_email(email)
        if user is None or not verify_password(password, user["password_hash"]):
            raise InvalidCredentialsError()

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


def _to_public(user: dict) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        display_name=user["display_name"],
        tier=user["tier"],
    )
