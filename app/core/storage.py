import base64
import hashlib
import threading
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core import config

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
    "llm_temperature",
    "llm_timeout",
    "llm_max_tokens",
    "llm_max_retries",
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
    llm_temperature: Mapped[str] = mapped_column(String(16), default="")
    llm_timeout: Mapped[str] = mapped_column(String(16), default="")
    llm_max_tokens: Mapped[str] = mapped_column(String(16), default="")
    llm_max_retries: Mapped[str] = mapped_column(String(16), default="")
    llm_base_url: Mapped[str] = mapped_column(String(256), default="")
    gcp_client_id: Mapped[str] = mapped_column(Text, default="")
    gcp_client_secret: Mapped[str] = mapped_column(Text, default="")
    gmail_refresh_token: Mapped[str] = mapped_column(Text, default="")
    gmail_email: Mapped[str] = mapped_column(String(256), default="")
    updated_at: Mapped[str] = mapped_column(String(64), default="")


class GmailAccount(Base):
    __tablename__ = "gmail_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), unique=True)
    label: Mapped[str] = mapped_column(String(64), default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PendingSend(Base):
    __tablename__ = "pending_send"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draft_id: Mapped[str] = mapped_column(String(256), default="")
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
        _migrate(_engine)
    return _engine


def _migrate(engine) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "settings" in tables:
        existing = {col["name"] for col in inspector.get_columns("settings")}
        for column, ddl in (
            ("llm_temperature", "VARCHAR(16) DEFAULT ''"),
            ("llm_timeout", "VARCHAR(16) DEFAULT ''"),
            ("llm_max_tokens", "VARCHAR(16) DEFAULT ''"),
            ("llm_max_retries", "VARCHAR(16) DEFAULT ''"),
        ):
            if column not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE settings ADD COLUMN {column} {ddl}"))

    if "pending_send" in tables:
        existing = {col["name"] for col in inspector.get_columns("pending_send")}
        for column, ddl in (
            ("account_id", "INTEGER"),
            ("draft_id", "VARCHAR(256) DEFAULT ''"),
        ):
            if column not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE pending_send ADD COLUMN {column} {ddl}"))

    _migrate_legacy_gmail(engine)


def _migrate_legacy_gmail(engine) -> None:
    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(GmailAccount)) or 0
        if count:
            return
        row = session.get(Settings, 1)
        if row is None or not row.gmail_refresh_token:
            return
        token = _decrypt(row.gmail_refresh_token)
        if not token:
            return
        session.add(
            GmailAccount(
                email=row.gmail_email or "unknown",
                label="",
                refresh_token=_encrypt(token),
                is_default=True,
            )
        )
        session.commit()


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
        "llm_temperature": row.llm_temperature,
        "llm_timeout": row.llm_timeout,
        "llm_max_tokens": row.llm_max_tokens,
        "llm_max_retries": row.llm_max_retries,
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


def setup_state() -> dict:
    s = get_settings()
    account_count = count_gmail_accounts()
    bot_ok = bool(s.get("bot_token"))
    llm_ok = bool(s.get("llm_api_key"))
    gcp_ok = bool(s.get("gcp_client_id") and s.get("gcp_client_secret"))
    gmail_ok = account_count > 0
    default = get_gmail_account()
    return {
        "bot_configured": bot_ok,
        "bot_username": s.get("bot_username"),
        "ui_language": s.get("ui_language") or "vi",
        "llm_configured": llm_ok,
        "gcp_configured": gcp_ok,
        "gmail_configured": gmail_ok,
        "gmail_email": (default or {}).get("email", ""),
        "gmail_account_count": account_count,
        "all_done": bot_ok and llm_ok and gcp_ok and gmail_ok,
    }


# ---------------------------------------------------------------------------
# Gmail accounts
# ---------------------------------------------------------------------------

def _account_public(row: GmailAccount) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "label": row.label or "",
        "is_default": bool(row.is_default),
    }


def list_gmail_accounts() -> list[dict]:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            rows = session.scalars(
                select(GmailAccount).order_by(
                    GmailAccount.is_default.desc(), GmailAccount.id
                )
            ).all()
            return [_account_public(r) for r in rows]


def count_gmail_accounts() -> int:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            return int(session.scalar(select(func.count()).select_from(GmailAccount)) or 0)


def get_gmail_account(account_id: int | None = None) -> dict | None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            if account_id is not None:
                row = session.get(GmailAccount, account_id)
            else:
                row = session.scalars(
                    select(GmailAccount)
                    .order_by(GmailAccount.is_default.desc(), GmailAccount.id)
                ).first()
            if row is None:
                return None
            data = _account_public(row)
            data["refresh_token"] = _decrypt(row.refresh_token)
            return data


def add_gmail_account(email: str, refresh_token: str, label: str = "") -> int:
    email = (email or "").strip()
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.scalars(
                select(GmailAccount).where(GmailAccount.email == email)
            ).first()
            has_any = bool(session.scalar(select(func.count()).select_from(GmailAccount)))
            if row is None:
                row = GmailAccount(
                    email=email,
                    label=label or "",
                    refresh_token=_encrypt(refresh_token),
                    is_default=not has_any,
                )
                session.add(row)
                session.commit()
                return int(row.id)
            row.refresh_token = _encrypt(refresh_token)
            if label:
                row.label = label
            session.commit()
            return int(row.id)


def remove_gmail_account(account_id: int) -> None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.get(GmailAccount, account_id)
            if row is None:
                return
            was_default = bool(row.is_default)
            session.delete(row)
            session.commit()
            if was_default:
                replacement = session.scalars(
                    select(GmailAccount).order_by(GmailAccount.id)
                ).first()
                if replacement is not None:
                    replacement.is_default = True
                    session.commit()


def set_default_gmail_account(account_id: int) -> None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            for row in session.scalars(select(GmailAccount)).all():
                row.is_default = row.id == account_id
            session.commit()


def update_gmail_account(account_id: int, label: str | None = None) -> None:
    if label is None:
        return
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.get(GmailAccount, account_id)
            if row is not None:
                row.label = label
                session.commit()


def clear_gmail() -> None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            for row in session.scalars(select(GmailAccount)).all():
                session.delete(row)
            session.commit()


# ---------------------------------------------------------------------------
# Pending sends
# ---------------------------------------------------------------------------

def create_pending_send(
    to_addr: str,
    subject: str,
    body: str,
    account_id: int | None = None,
    draft_id: str | None = None,
) -> int:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = PendingSend(
                to_addr=to_addr,
                subject=subject,
                body=body,
                account_id=account_id,
                draft_id=draft_id or "",
            )
            session.add(row)
            session.commit()
            return int(row.id)


def latest_pending_id() -> int:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            value = session.scalar(select(func.max(PendingSend.id)))
            return int(value or 0)


def get_pending_send(pending_id: int) -> dict | None:
    with _lock:
        engine = _get_engine()
        with Session(engine) as session:
            row = session.get(PendingSend, pending_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "account_id": row.account_id,
                "draft_id": row.draft_id or "",
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
