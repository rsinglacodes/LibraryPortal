from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

    # Roboflow damage-detection
    ROBOFLOW_API_KEY: str = os.getenv("ROBOFLOW_API_KEY", "")
    ROBOFLOW_WORKSPACE: str = os.getenv("ROBOFLOW_WORKSPACE", "amvi")
    ROBOFLOW_WORKFLOW_ID: str = os.getenv(
        "ROBOFLOW_WORKFLOW_ID",
        "book-damage-detection-and-localization-1787063130435",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
