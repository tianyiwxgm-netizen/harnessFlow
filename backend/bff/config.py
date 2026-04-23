from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bff_version: str = "0.1.0"
    bff_port: int = 8001
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    pid_header_name: str = "X-Harness-Pid"

    model_config = SettingsConfigDict(env_prefix="HARNESS_", env_file=".env", extra="ignore")


settings = Settings()
