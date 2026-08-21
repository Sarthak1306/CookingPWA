import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str = os.environ.get("KITCHEN_DB_PATH", "kitchen.db")
    cookie_secure: bool = os.environ.get("KITCHEN_COOKIE_SECURE", "1") != "0"
    static_dir: str = os.environ.get("KITCHEN_STATIC_DIR", "web/dist")
    # OpenRouter / model config land in P2 — not read yet, but the env var
    # names are reserved here so .env.example stays the single source of truth.
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    model_name: str = os.environ.get("KITCHEN_MODEL_NAME", "")


settings = Settings()
