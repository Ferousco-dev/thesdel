import pytest

from app.shared.deps import CurrentUser, require_tier
from app.shared.errors import UpgradeRequiredError


def _user(tier: str) -> CurrentUser:
    return CurrentUser(id="507f1f77bcf86cd799439011", tier=tier, email="a@b.com", display_name="A")


@pytest.mark.parametrize(
    ("user_tier", "required_tier", "should_pass"),
    [
        ("free", "free", True),
        ("free", "premium", False),
        ("premium", "premium", True),
        ("premium", "pro", False),
        ("pro", "premium", True),
        ("pro", "pro", True),
    ],
)
async def test_require_tier(user_tier, required_tier, should_pass):
    check = require_tier(required_tier)
    if should_pass:
        result = await check(_user(user_tier))
        assert result.tier == user_tier
    else:
        with pytest.raises(UpgradeRequiredError):
            await check(_user(user_tier))
