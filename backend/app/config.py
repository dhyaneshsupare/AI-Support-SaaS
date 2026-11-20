from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ai_support_saas"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    hf_token: str = ""
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"

    chroma_persist_dir: str = "./chroma_data"
    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 10
    upload_dir: str = "./uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
