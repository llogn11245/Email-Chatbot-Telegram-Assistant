import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core import storage
from app.core.observability.errors import GmailError

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

_cache: dict[int, object] = {}


def _gcp_credentials() -> tuple[str, str]:
    settings = storage.get_settings()
    client_id = settings.get("gcp_client_id")
    client_secret = settings.get("gcp_client_secret")
    if not (client_id and client_secret):
        raise GmailError("Chưa cấu hình Google OAuth client.")
    return client_id, client_secret


def _build_service(client_id: str, client_secret: str, refresh_token: str):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _get_service(account_id: int | None = None):
    account = storage.get_gmail_account(account_id)
    if not account or not account.get("refresh_token"):
        raise GmailError(
            "Chưa kết nối tài khoản Gmail nào. Mở Settings và bấm 'Add account'."
        )
    key = account["id"]
    if key in _cache:
        return _cache[key]
    client_id, client_secret = _gcp_credentials()
    service = _build_service(client_id, client_secret, account["refresh_token"])
    _cache[key] = service
    return service


def clear_cache() -> None:
    _cache.clear()


def fetch_profile_email(refresh_token: str) -> str:
    client_id, client_secret = _gcp_credentials()
    service = _build_service(client_id, client_secret, refresh_token)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def get_profile_email(account_id: int | None = None) -> str:
    service = _get_service(account_id)
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def _decode(data: str | None) -> str:
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _body_from_payload(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {}) or {}
    if mime == "text/plain" and body.get("data"):
        return _decode(body["data"])
    parts = payload.get("parts") or []
    for part in parts:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return _decode(part["body"]["data"])
    for part in parts:
        if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
            return _decode(part["body"]["data"])
    return ""


def _headers(msg: dict, wanted) -> dict:
    out = {}
    for header in (msg.get("payload", {}).get("headers") or []):
        name = header.get("name", "").lower()
        if name in wanted:
            out[name] = header.get("value", "")
    return out


def _account_tag(account_id: int | None) -> dict:
    account = storage.get_gmail_account(account_id) or {}
    return {
        "account_id": account.get("id"),
        "account_email": account.get("email", ""),
        "account_label": account.get("label", ""),
    }


def search_emails(query: str, max_results: int = 10, account_id: int | None = None) -> list[dict]:
    service = _get_service(account_id)
    tag = _account_tag(account_id)
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = response.get("messages", [])
    result = []
    for item in messages:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = _headers(msg, {"from", "subject", "date"})
        result.append(
            {
                "id": msg["id"],
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "snippet": msg.get("snippet", ""),
                **tag,
            }
        )
    result.sort(key=lambda m: m.get("date") or "", reverse=True)
    return result


def read_email(message_id: str, max_chars: int = 8000, account_id: int | None = None) -> dict:
    service = _get_service(account_id)
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = _headers(msg, {"from", "to", "subject", "date"})
    body = _body_from_payload(msg.get("payload", {}))
    if len(body) > max_chars:
        body = body[:max_chars] + "\n...[bị cắt ngắn]"
    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "body": body,
        "snippet": msg.get("snippet", ""),
        **_account_tag(account_id),
    }


def _build_raw(to_addr: str, subject: str, body: str) -> str:
    message = MIMEText(body, "plain", "utf-8")
    message["To"] = to_addr
    message["Subject"] = subject
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def create_draft(to_addr: str, subject: str, body: str, account_id: int | None = None) -> str:
    """Tạo bản nháp trong Gmail (cần scope gmail.compose). Trả về draft id."""
    service = _get_service(account_id)
    raw = _build_raw(to_addr, subject, body)
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return draft.get("id", "")


def send_draft(draft_id: str, account_id: int | None = None) -> str:
    service = _get_service(account_id)
    sent = (
        service.users()
        .drafts()
        .send(userId="me", body={"id": draft_id})
        .execute()
    )
    return sent.get("id", "")


def delete_draft(draft_id: str, account_id: int | None = None) -> None:
    service = _get_service(account_id)
    service.users().drafts().delete(userId="me", id=draft_id).execute()


def send_email(to_addr: str, subject: str, body: str, account_id: int | None = None) -> str:
    service = _get_service(account_id)
    raw = _build_raw(to_addr, subject, body)
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw})
        .execute()
    )
    return sent.get("id", "")


def parse_client_secret_json(raw: str) -> dict:
    import json

    data = json.loads(raw)
    entry = data.get("installed") or data.get("web")
    if not entry:
        raise ValueError("File không chứa mục 'installed' hoặc 'web'.")
    return {
        "client_id": entry.get("client_id"),
        "client_secret": entry.get("client_secret"),
    }
