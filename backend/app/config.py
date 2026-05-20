from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AutoFlowOps"
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    frontend_url: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./autoflowops.db"

    log_level: str = "INFO"
    default_timezone: str = "America/Sao_Paulo"
    enable_demo_mode: bool = True

    # JWT authentication
    jwt_secret_key: str = "change-me-before-production"
    jwt_access_token_expire_minutes: int = 60

    # Bootstrap admin account (created on first startup if users table is empty)
    admin_email: str = "admin@autoflowops.local"
    admin_password: str = "changeme"
    admin_name: str = "Admin"

    # SSRF protection for HTTP jobs
    enable_ssrf_protection: bool = True
    allow_private_network_targets: bool = False

    # Rate limiting (in-memory, per process)
    webhook_rate_limit_per_minute: int = 60
    api_rate_limit_per_minute: int = 120

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
