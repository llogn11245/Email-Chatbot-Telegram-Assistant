import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

load_dotenv(ROOT_DIR / ".env", override=False)


def _get(name: str, default: str | None = None):
    return os.getenv(name, default)


# Bot token KHÔNG còn đọc từ env — được nhập qua web interface và lưu (mã hoá) trong DB.
TELEGRAM_ADMIN_ID = None
try:
    TELEGRAM_ADMIN_ID = int(_get("TELEGRAM_ADMIN_ID", "0") or 0) or None
except ValueError:
    TELEGRAM_ADMIN_ID = None

SECRET_KEY = _get("SECRET_KEY", "dev-secret-change-me")
WEB_HOST = _get("WEB_HOST", "0.0.0.0")
WEB_PORT = int(_get("WEB_PORT", "8000"))
WEB_URL = _get("WEB_URL", f"http://localhost:{WEB_PORT}").rstrip("/")
REDIRECT_URI = _get("REDIRECT_URI", f"{WEB_URL}/")
ADMIN_PASSWORD = _get("ADMIN_PASSWORD")
RUN_MODE = _get("RUN_MODE", "both").lower()

DATABASE_URL = _get(
    "DATABASE_URL",
    "postgresql+psycopg://chatbot:chatbot@localhost:5432/chatbot",
)

GOOGLE_CLIENT_ID = _get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _get("GOOGLE_CLIENT_SECRET")
