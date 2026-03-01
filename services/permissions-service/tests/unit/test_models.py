import pytest
from app.models.permissions import DEFAULT_PERMISSIONS, UserPermissions
from app.models.subscriptions import SUBSCRIPTION_TIERS, Subscription
from app.models.usage import FeatureUsage


class TestUserPermissions:
    def test_default_permissions_flags(self):
        perms = UserPermissions(user_id="user123")
        assert perms.role == "user"
        assert perms.is_premium is False
        assert perms.is_admin is False
        assert perms.permissions["ad_free"] is False
        assert perms.permissions["ai_text_generation"] is False
        assert perms.permissions["ai_image_generation"] is False
        assert perms.permissions["advanced_search"] is False

    def test_default_permissions_has_all_keys(self):
        perms = UserPermissions(user_id="user123")
        for key in DEFAULT_PERMISSIONS:
            assert key in perms.permissions

    def test_custom_permissions(self):
        custom = {"ad_free": True, "premium_features": True}
        perms = UserPermissions(user_id="user123", permissions=custom)
        assert perms.permissions["ad_free"] is True
        assert perms.permissions["premium_features"] is True


class TestSubscription:
    def test_default_subscription(self):
        sub = Subscription(user_id="user123")
        assert sub.tier == "free"
        assert sub.status == "active"
        assert sub.stripe_subscription_id is None

    def test_premium_subscription(self):
        sub = Subscription(user_id="user123", tier="premium", status="active")
        assert sub.tier == "premium"


class TestSubscriptionTiers:
    def test_free_tier_exists(self):
        assert "free" in SUBSCRIPTION_TIERS
        assert SUBSCRIPTION_TIERS["free"]["price"] == 0

    def test_premium_tier_exists(self):
        assert "premium" in SUBSCRIPTION_TIERS
        assert SUBSCRIPTION_TIERS["premium"]["price"] == 4.99

    def test_ultra_tier_exists(self):
        assert "ultra" in SUBSCRIPTION_TIERS
        assert SUBSCRIPTION_TIERS["ultra"]["price"] == 9.99

    def test_ultra_has_unlimited_ai(self):
        limits = SUBSCRIPTION_TIERS["ultra"]["feature_limits"]
        assert limits["ai_text_generation"] == -1
        assert limits["ai_image_generation"] == -1

    def test_free_tier_permissions(self):
        perms = SUBSCRIPTION_TIERS["free"]["permissions"]
        assert perms["ad_free"] is False
        assert perms["ai_text_generation"] is True
        assert perms["ai_image_generation"] is False


class TestFeatureUsage:
    def test_default_usage(self):
        usage = FeatureUsage(user_id="user123", feature="ai_text_generation")
        assert usage.used == 0
        assert usage.limit == 0
        assert usage.bonus == 0
        assert usage.last_used_at is None

    def test_period_end_set(self):
        usage = FeatureUsage(user_id="user123", feature="ai_text_generation")
        assert usage.period_end > usage.period_start
