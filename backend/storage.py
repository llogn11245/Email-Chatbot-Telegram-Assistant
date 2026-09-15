import base64
import hashlib
import threading
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend import config

_lock = threading.Lock()
_engine = None

_ENCRYPTED_FIELDS = {
    "llm_api_key",
    "gcp_client_secret",
    "gmail_refresh_token",
    "bot_token",
}
_SETTINGS_FIELDS = {
    "bot_token",
    "bot_username",
    "ui_language",
    "llm_provider",
    "llm_model",
    "llm_api_key",
    "llm_base_url",
    "gcp_client_id",
    "gcp_client_secret",
    "gmail_refresh_token",
    "gmail_email",
}
_LANGUAGES = {"vi", "en"}


class Base(DeclarativeBase):
    pass


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_token: Mapped[str] = mapped_column(Text, default="")
    bot_username: Mapped[str] = mapped_column(String(128), default="")
    ui_language: Mapped[str] = mapped_column(String(8), default="vi")
    llm_provider: Mapped[str] = mapped_column(String(32), default="")
    llm_model: Mapped[str] = mapped_column(String(128), default="")
    llm_api_key: Mapped[str] = mapped_column(Text, default="")
    llm_base_url: Mapped[str] = mapped_column(String(256), default="")
    gcp_client_id: Mapped[str] = mapped_column(Text, default="")
    gcp_client_secret: Mapped[str] = mapped_column(Text, default="")
    gmail_refresh_token: Mapped[str] = mapped_column(Text, default="")
    gmail_email: Mapped[str] = mapped_column(String(256), default="")
    updated_at: Mapped[str] = mapped_column(String(64), default="")


class PendingSend(Base):
    __tablename__ = "pending_send"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    to_addr: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(String(16), default="pending")


def _fernet() -> Fernet:
    digest = hashlib.sha256(config.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().decrypt(value.encode()).decode()


def _get_engine():
    global _engine
    if _engine is None:
        url = config.DATABASE_URL
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
        Base.metadata.create_all(_engine)
    return _engine


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get_or_create_settings(session: Session) -> Settings:
    row = session.get(Settings, 1)
    if row is None:
        row = Settings(id=1)
        session.add(row)
        session.commit()
    return row


def _serialize(row: Settings) -> dict:
    data = {
        "bot_token": row.bot_token,
        "bot_username": row.bot_username,
        "ui_language": row.ui_language or "vi",
        "llm_provider": row.llm_provider,
        "llm_model": row.llm_model,
        "llm_api_key": row.llm_api_key,
        "llm_base_url": row.llm_base_url,
        "gcp_client_id": row.gcp_client_id,
        "gcp_client_secret": row.gcp_client_secret,
        "gmail_refresh_token": row.gmail_refresh_token,
        "gmail_email": row.gmail_email,
        "updated_at": row.updated_at,
    }
    for field in _ENCRYPTED_FIELDS:
        if data.get(field):
            data[field] = _decrypt(data[field])
    return data


def get_settings() -> dict:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = _get_or_create_settings(session)
            return _serialize(row)


def update_settings(**fields) -> dict:
    allowed = {k: v for k, v in fields.items() if k in _SETTINGS_FIELDS and v is not None}
    if "ui_language" in allowed and allowed["ui_language"] not in _LANGUAGES:
        allowed["ui_language"] = "vi"
    for field in _ENCRYPTED_FIELDS:
        if field in allowed:
            allowed[field] = _encrypt(str(allowed[field]))
    allowed["updated_at"] = _now()
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = _get_or_create_settings(session)
            for key, value in allowed.items():
                setattr(row, key, value)
            session.commit()
            return _serialize(row)


def clear_gmail() -> None:
    update_settings(gmail_refresh_token="", gmail_email="")


def setup_state() -> dict:
    s = get_settings()
    bot_ok = bool(s.get("bot_token"))
    llm_ok = bool(s.get("llm_api_key"))
    gcp_ok = bool(s.get("gcp_client_id") and s.get("gcp_client_secret"))
    gmail_ok = bool(s.get("gmail_refresh_token"))
    return {
        "bot_configured": bot_ok,
        "bot_username": s.get("bot_username"),
        "ui_language": s.get("ui_language") or "vi",
        "llm_configured": llm_ok,
        "gcp_configured": gcp_ok,
        "gmail_configured": gmail_ok,
        "gmail_email": s.get("gmail_email"),
        "all_done": bot_ok and llm_ok and gcp_ok and gmail_ok,
    }


def create_pending_send(to_addr: str, subject: str, body: str) -> int:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = PendingSend(to_addr=to_addr, subject=subject, body=body)
            session.add(row)
            session.commit()
            return int(row.id)


def get_pending_send(pending_id: int) -> dict | None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.get(PendingSend, pending_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "to_addr": row.to_addr,
                "subject": row.subject,
                "body": row.body,
                "status": row.status,
            }


def set_pending_status(pending_id: int, status: str) -> None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.get(PendingSend, pending_id)
            if row is not None:
                row.status = status
                session.commit()
