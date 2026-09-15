import base64
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from backend import storage
from backend.gmail_oauth import GMAIL_SCOPES, TOKEN_URI

_cache: dict = {"refresh_token": None, "service": None}


class GmailError(RuntimeError):
    pass


def _get_service():
    settings = storage.get_settings()
    client_id = settings.get("gcp_client_id")
    client_secret = settings.get("gcp_client_secret")
    refresh_token = settings.get("gmail_refresh_token")
    if not (client_id and client_secret and refresh_token):
        raise GmailError("Gmail chưa được kết nối. Mở control panel và bấm 'Connect Gmail'.")

    if _cache.get("refresh_token") == refresh_token and _cache.get("service"):
        return _cache["service"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
    )
    creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    _cache["refresh_token"] = refresh_token
    _cache["service"] = service
    return service


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


def get_profile_email() -> str:
    service = _get_service()
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    service = _get_service()
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
            }
        )
    result.sort(key=lambda m: m.get("date") or "", reverse=True)
    return result


def read_email(message_id: str, max_chars: int = 8000) -> dict:
    service = _get_service()
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
    }


def send_email(to_addr: str, subject: str, body: str) -> str:
    service = _get_service()
    message = MIMEText(body, "plain", "utf-8")
    message["To"] = to_addr
    message["Subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
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
