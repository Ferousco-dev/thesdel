"""Shared FastAPI dependencies: current-user resolution and tier gating.

Per RULES.md #2 and docs/SECURITY.md §4: authorization is never inferred
from a JWT claim alone beyond identifying *who* the requester is. Tier is
re-resolved from the database on every request that gates a feature, so a
tier downgrade takes effect immediately rather than waiting out a stale
access token's lifetime.
"""

from typing import Annotated

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.db import get_db
from app.shared.errors import ForbiddenError, NotFoundError, UnauthenticatedError, UpgradeRequiredError
from app.shared.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)

TIER_RANK = {"free": 0, "premium": 1, "pro": 2}


class CurrentUser:
    __slots__ = ("id", "tier", "email", "display_name")

    def __init__(self, id: str, tier: str, email: str, display_name: str) -> None:
        self.id = id
        self.tier = tier
        self.email = email
        self.display_name = display_name


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    if credentials is None:
        raise UnauthenticatedError()

    payload = decode_access_token(credentials.credentials)
    user_id = payload["sub"]

    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise UnauthenticatedError()

    current = CurrentUser(
        id=str(user["_id"]),
        tier=user["tier"],
        email=user["email"],
        display_name=user["display_name"],
    )

    # bind for structured logging without leaking PII (id only)
    import structlog

    structlog.contextvars.bind_contextvars(user_id=current.id)

    return current


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_tier(min_tier: str):
    """Usage: Depends(require_tier("premium")). Rejects with 403 +
    upgrade_required before any downstream cost is incurred, per
    docs/API.md §3."""

    async def _check(user: CurrentUserDep) -> CurrentUser:
        if TIER_RANK.get(user.tier, -1) < TIER_RANK.get(min_tier, 99):
            raise UpgradeRequiredError(details={"required_tier": min_tier, "current_tier": user.tier})
        return user

    return _check


class ClassMembership:
    __slots__ = ("class_id", "user_id", "role")

    def __init__(self, class_id: str, user_id: str, role: str) -> None:
        self.class_id = class_id
        self.user_id = user_id
        self.role = role

    @property
    def is_rep(self) -> bool:
        return self.role == "rep"


def _parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise NotFoundError() from exc


async def require_class_membership(
    class_id: Annotated[str, Path()],
    user: CurrentUserDep,
) -> ClassMembership:
    """Verifies the current user is a member of the class in the path,
    re-checked from the database on every request. An object ID existing is
    never sufficient authorization on its own — see docs/SECURITY.md §4 and
    RULES.md #4 (IDOR/BOLA mitigation)."""
    db = get_db()
    membership = await db.class_members.find_one(
        {"class_id": _parse_object_id(class_id), "user_id": _parse_object_id(user.id)}
    )
    if membership is None:
        # 404, not 403 — do not reveal whether the class exists to a
        # non-member, per docs/API.md §4.
        raise NotFoundError()
    return ClassMembership(class_id=class_id, user_id=user.id, role=membership["role"])


ClassMembershipDep = Annotated[ClassMembership, Depends(require_class_membership)]


async def require_class_rep(
    membership: ClassMembershipDep,
) -> ClassMembership:
    if not membership.is_rep:
        raise ForbiddenError("Only the class rep can do that.")
    return membership


ClassRepDep = Annotated[ClassMembership, Depends(require_class_rep)]
