import os
import secrets
import shutil
import sys
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "ChatbotGmail"
APP_AUTHOR = "ChatbotGmail"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Nơi chứa tài nguyên đi kèm (assets...) khi đóng gói; repo root khi dev."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return _PROJECT_ROOT


def base_dir() -> Path:
    """Thư mục chứa data/ và logs/ — ngang cấp với app/, assets/ (repo khi dev; cạnh exe khi đóng gói)."""
    env = os.getenv("CHATBOT_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _PROJECT_ROOT


def _legacy_data_dir() -> Path:
    return Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))


def _legacy_log_dir() -> Path:
    return Path(user_log_dir(APP_NAME, appauthor=False))


def data_dir() -> Path:
    path = base_dir() / "data"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = _legacy_data_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def log_dir() -> Path:
    path = base_dir() / "logs"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = _legacy_log_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def _secret_file() -> Path:
    return data_dir() / "secret.key"


def load_or_create_secret() -> str:
    env_value = os.getenv("SECRET_KEY")
    if env_value:
        return env_value
    path = _secret_file()
    if path.is_file():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value
