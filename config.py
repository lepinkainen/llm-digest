from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database settings
    DATABASE_URL: str = "llm_digest.db"

    # LLM settings
    LLM_DEFAULT_MODEL: str = "gpt-4o-mini"
    LLM_DEFAULT_FORMAT: str = "bullet"
    LLM_TIMEOUT: int = 120
    LLM_DEBUG_MODE: bool = False

    # OpenGraph settings
    OG_EXTRACTOR_TIMEOUT: int = 30

    # Web app settings
    WEB_APP_HOST: str = "127.0.0.1"
    WEB_APP_PORT: int = 8000
    WEB_APP_RELOAD: bool = True


settings = Settings()
