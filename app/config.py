import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: str = os.environ.get("KITCHEN_DB_PATH", "kitchen.db")
    cookie_secure: bool = os.environ.get("KITCHEN_COOKIE_SECURE", "1") != "0"
    static_dir: str = os.environ.get("KITCHEN_STATIC_DIR", "web/dist")
    openrouter_api_key: str = os.environ.get("OPENROUTER_API_KEY", "")
    model_name: str = os.environ.get("KITCHEN_MODEL_NAME", "")
    model_name_cheap: str = os.environ.get("KITCHEN_MODEL_NAME_CHEAP", "")
    monthly_call_cap: int = int(os.environ.get("KITCHEN_MONTHLY_CALL_CAP", "300"))


settings = Settings()
