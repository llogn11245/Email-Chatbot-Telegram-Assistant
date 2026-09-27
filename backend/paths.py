import os
import secrets
import sys
from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "ChatbotGmail"
APP_AUTHOR = "ChatbotGmail"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    path = Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = Path(user_log_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def frontend_dist() -> Path:
    return resource_path("frontend", "dist")


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
