import os

from app.core import paths

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

APP_NAME = paths.APP_NAME
APP_VERSION = "0.2.0"

# .env chỉ dùng khi chạy dev (không ở bản đóng gói); env thật luôn được ưu tiên.
if not paths.is_frozen() and load_dotenv is not None:
    _env_file = paths.app_root() / ".env"
    if _env_file.is_file():
        load_dotenv(_env_file, override=False)


def _get(name: str, default: str | None = None):
    return os.getenv(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(_get(name, str(default)))
    except (TypeError, ValueError):
        return default


DATA_DIR = paths.data_dir()
LOG_DIR = paths.log_dir()
SECRET_KEY = paths.load_or_create_secret()

try:
    TELEGRAM_ADMIN_ID = int(_get("TELEGRAM_ADMIN_ID", "0") or 0) or None
except ValueError:
    TELEGRAM_ADMIN_ID = None

LOG_LEVEL = _get("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = _get_int("LOG_RETENTION_DAYS", 30)

DATABASE_URL = _get(
    "DATABASE_URL",
    f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}",
)

GOOGLE_CLIENT_ID = _get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _get("GOOGLE_CLIENT_SECRET")
