from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    redis_url: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""
    github_token: str = ""

    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 10080

    gemini_api_key: str = ""
    llm_provider: str = "gemini"

    frontend_url: str = "http://localhost:5173"

    leetcode_session: str = ""
    leetcode_csrf_token: str = ""
    fetch_cf_statements: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
