import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from app.core import config, i18n, storage
from app.email import gmail_client
from app.email.gmail_client import AUTH_URI, GMAIL_SCOPES, TOKEN_URI


def get_gcp_credentials() -> tuple[str, str]:
    settings = storage.get_settings()
    client_id = config.GOOGLE_CLIENT_ID or settings.get("gcp_client_id")
    client_secret = config.GOOGLE_CLIENT_SECRET or settings.get("gcp_client_secret")
    if not (client_id and client_secret):
        raise RuntimeError("Chưa cấu hình Google OAuth client.")
    return client_id, client_secret


def build_auth_url(client_id: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> str:
    resp = requests.post(
        TOKEN_URI,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "Google không trả refresh_token. Hãy chắc chắn OAuth app đã publish "
            "(In production) thay vì ở trạng thái Testing."
        )
    return refresh_token


def finalize(code: str | None, error: str | None, redirect_uri: str, client_id: str, client_secret: str):
    """Đổi code -> refresh token -> lấy email -> lưu tài khoản. Trả (ok, message)."""
    lang = i18n.current_language()
    if error:
        return False, f"{i18n.t('oauth_google_error', lang)} {error}"
    if not code:
        return False, i18n.t("oauth_missing_code", lang)
    try:
        refresh_token = exchange_code(code, client_id, client_secret, redirect_uri)
    except Exception as exc:
        return False, f"{i18n.t('oauth_exchange_error', lang)} {exc}"
    try:
        email = gmail_client.fetch_profile_email(refresh_token)
    except Exception as exc:
        return False, f"{i18n.t('oauth_profile_error', lang)} {exc}"
    storage.add_gmail_account(email, refresh_token)
    gmail_client.clear_cache()
    return True, f"{i18n.t('oauth_connected', lang)} {email}."


def _done_html(title: str, message: str, ok: bool) -> str:
    color = "#16a34a" if ok else "#dc2626"
    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui,Segoe UI,sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;background:#f1f5f9}}
.card{{background:#fff;padding:32px 36px;border-radius:14px;box-shadow:0 4px 16px rgba(15,23,42,.08);
text-align:center;max-width:420px}} h2{{color:{color};margin:0 0 8px}} p{{color:#475569;margin:0}}</style>
</head><body><div class="card"><h2>{title}</h2><p>{message}</p>
<p style="margin-top:12px;color:#94a3b8">Bạn có thể đóng tab này và quay lại ứng dụng.</p>
</div></body></html>"""


class OAuthCallbackServer:
    """HTTP loopback nhỏ (stdlib) để nhận redirect OAuth của Google."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.port: int | None = None
        self.redirect_uri: str | None = None
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        handler = self._make_handler()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.port = self._httpd.server_address[1]
        self.redirect_uri = f"http://localhost:{self.port}/"
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="oauth-callback", daemon=True
        )
        self._thread.start()
        return self.redirect_uri

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # tắt log mặc định
                return

            def do_GET(self):  # noqa: N802
                params = parse_qs(urlparse(self.path).query)
                code = (params.get("code") or [None])[0]
                error = (params.get("error") or [None])[0]
                if not code and not error:
                    self._respond(200, "Chatbot Gmail", "Đang chờ đăng nhập Google...", True)
                    return
                ok, message = finalize(
                    code, error, server.redirect_uri, server.client_id, server.client_secret
                )
                title = i18n.t("oauth_ok_title") if ok else i18n.t("oauth_fail_title")
                self._respond(200 if ok else 400, title, message, ok)
                threading.Thread(target=server.stop, daemon=True).start()

            def _respond(self, status: int, title: str, message: str, ok: bool) -> None:
                body = _done_html(title, message, ok).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler

    def stop(self) -> None:
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            try:
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None


def start_callback_flow() -> tuple["OAuthCallbackServer", str]:
    client_id, client_secret = get_gcp_credentials()
    server = OAuthCallbackServer(client_id, client_secret)
    redirect_uri = server.start()
    url = build_auth_url(client_id, redirect_uri)
    return server, url
