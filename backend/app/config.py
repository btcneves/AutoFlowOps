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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
