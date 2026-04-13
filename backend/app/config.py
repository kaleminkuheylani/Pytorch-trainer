"""Application configuration."""

import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
STREAM_INTERVAL_SECONDS: int = int(os.getenv("STREAM_INTERVAL_SECONDS", "30"))
