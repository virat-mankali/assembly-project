import os

from dotenv import load_dotenv


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "gemini-2.5-flash"
MAX_AUDIO_SIZE_MB = 25
DB_PATH = os.getenv("DB_PATH", "database/bot_memory.db")


def require_env(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def validate_runtime_config() -> None:
    require_env("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    require_env("GROQ_API_KEY", GROQ_API_KEY)
    require_env("GEMINI_API_KEY", GEMINI_API_KEY)
