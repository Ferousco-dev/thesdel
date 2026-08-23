from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "thesdel"

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # Google Sign-In (ID-token flow via Google Identity Services — no
    # client secret needed, the backend just verifies the token's
    # signature and audience against this Client ID). See
    # docs/DECISIONS.md ADR-011.
    google_client_id: str = ""

    cors_origins: str = "http://localhost:5173"

    rate_limit_login_max: int = 5
    rate_limit_login_window_seconds: int = 60
    rate_limit_default_max: int = 100
    rate_limit_default_window_seconds: int = 60

    # Rate limits for the email-verification resend and password-reset
    # request endpoints — kept distinct from login/register per
    # docs/SECURITY.md §3 ("login/registration/password-reset endpoints
    # are rate-limited distinctly").
    rate_limit_verification_max: int = 5
    rate_limit_verification_window_seconds: int = 3600
    rate_limit_password_reset_max: int = 5
    rate_limit_password_reset_window_seconds: int = 3600

    # Opaque-token TTLs — see docs/DECISIONS.md ADR-010 for why these
    # specific values within docs/SECURITY.md's stated 15-60 min range.
    email_verification_ttl_minutes: int = 60
    password_reset_ttl_minutes: int = 30

    # AI usage caps — config, not hardcoded, per docs/SECURITY.md §3 and
    # docs/DECISIONS.md ADR-004. Suggested defaults from the Backend Spec
    # §6; tune after real cost-per-call data exists.
    ai_cap_study_regenerate_monthly: int = 15
    ai_cap_life_adjust_monthly: int = 25

    llm_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "Thesdel <no-reply@thesdel.app>"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    fcm_server_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
