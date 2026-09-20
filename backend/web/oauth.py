from urllib.parse import urlencode

import requests
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from backend import config, i18n, storage
from backend.email_services import gmail_client
from backend.email_services.gmail_client import AUTH_URI, GMAIL_SCOPES, TOKEN_URI


def get_gcp_credentials() -> tuple[str, str]:
    settings = storage.get_settings()
    client_id = config.GOOGLE_CLIENT_ID or settings.get("gcp_client_id")
    client_secret = config.GOOGLE_CLIENT_SECRET or settings.get("gcp_client_secret")
    if not (client_id and client_secret):
        raise HTTPException(status_code=400, detail="Chưa có OAuth client. Hãy hoàn tất bước OAuth.")
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


def oauth_done_page(title: str, message: str) -> HTMLResponse:
    back = i18n.t("back_to_panel")
    html = f"""
    <!DOCTYPE html>
    <html lang="vi"><head><meta charset="utf-8">
    <title>{title}</title>
    <style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;
    height:100vh;margin:0;background:#f5f7fa}} .card{{background:#fff;padding:32px;border-radius:12px;
    box-shadow:0 2px 12px rgba(0,0,0,.08);text-align:center;max-width:420px}}
    a{{display:inline-block;margin-top:16px;color:#1a73e8;text-decoration:none}}</style></head>
    <body><div class="card"><h2>{title}</h2><p>{message}</p>
    <a href="/">{back}</a></div></body></html>
    """
    return HTMLResponse(html)


def finalize_oauth(code: str | None, error: str | None) -> HTMLResponse:
    lang = i18n.current_language()
    client_id, client_secret = get_gcp_credentials()
    if error:
        return oauth_done_page(
            i18n.t("oauth_fail_title", lang), f"{i18n.t('oauth_google_error', lang)} {error}"
        )
    if not code:
        return oauth_done_page(i18n.t("oauth_fail_title", lang), i18n.t("oauth_missing_code", lang))
    try:
        refresh_token = exchange_code(code, client_id, client_secret, config.REDIRECT_URI)
        storage.update_settings(gmail_refresh_token=refresh_token)
    except HTTPException:
        raise
    except Exception as exc:
        return oauth_done_page(
            i18n.t("oauth_fail_title", lang), f"{i18n.t('oauth_exchange_error', lang)} {exc}"
        )
    try:
        email = gmail_client.get_profile_email()
        storage.update_settings(gmail_email=email)
    except Exception:
        email = ""
    text = f"{i18n.t('oauth_connected', lang)} {email}." if email else f"{i18n.t('oauth_connected', lang)}."
    return oauth_done_page(i18n.t("oauth_ok_title", lang), f"{text} {i18n.t('oauth_close', lang)}")
