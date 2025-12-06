from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    server_host: str = Field("0.0.0.0", env="CAMPBOT_SERVER_HOST")
    server_port: int = Field(8000, env="CAMPBOT_SERVER_PORT")
    server_reload: bool = Field(True, env="CAMPBOT_SERVER_RELOAD")
    server_log_level: str = Field("info", env="CAMPBOT_SERVER_LOG_LEVEL")

    database_url: str = Field(..., env="DATABASE_URL")

    amocrm_client_id: str = Field("", env="CAMPBOT_AMOCRM_CLIENT_ID")
    amocrm_client_secret: str = Field("", env="CAMPBOT_AMOCRM_CLIENT_SECRET")
    amocrm_redirect_uri: str = Field("", env="CAMPBOT_AMOCRM_REDIRECT_URI")
    amocrm_subdomain: str = Field("", env="CAMPBOT_AMOCRM_SUBDOMAIN")

    telegram_bot_token: str = Field("", env="CAMPBOT_TELEGRAM_BOT_TOKEN")
    telegram_webhook_url: str = Field("", env="CAMPBOT_TELEGRAM_WEBHOOK_URL")
    telegram_webhook_path: str = Field(
        "/telegram/webhook",
        env="CAMPBOT_TELEGRAM_WEBHOOK_PATH",
    )

    storage_path: str = Field("./data", env="CAMPBOT_STORAGE_PATH")

    @property
    def amocrm_base_url(self) -> str:
        sub = self.amocrm_subdomain.strip().rstrip("/")
        if not sub:
            return ""
        return f"https://{sub}.amocrm.ru"

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
config = settings
