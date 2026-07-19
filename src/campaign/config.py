from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"
    log_json: bool = False
    campaign_demo_mode: bool = False

    database_url: str = "sqlite+aiosqlite:///campaign_v2.db"
    redis_url: str = "redis://localhost:6379/0"

    anthropic_api_key: str = ""
    llm_synthesis_model: str = "claude-opus-4-8"
    llm_extraction_model: str = "claude-sonnet-5"
    llm_prompt_cache: bool = True

    ea_enabled_default: bool = False
    ea_email_default: str = ""

    personalization_min_score: int = Field(70, ge=0, le=100)
    company_profile_ttl_days: int = Field(7, ge=1)

    # Draft quality loop (draft → review → refine → repeat)
    draft_review_max_iterations: int = Field(2, ge=0, le=5)
    draft_review_pass_score: int = Field(85, ge=0, le=100)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
