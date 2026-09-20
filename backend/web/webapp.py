import json

from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config, storage
from backend.email_services import gmail_client
from backend.web import oauth

_bot_manager = None


def set_bot_manager(manager) -> None:
    global _bot_manager
    _bot_manager = manager


class BotSetupBody(BaseModel):
    bot_token: str


class LanguageBody(BaseModel):
    language: str


class LlmSetupBody(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str
    base_url: str | None = None


class GcpSetupBody(BaseModel):
    client_id: str | None = None
    client_secret: str | None = None
    client_secret_json: str | None = None


def _require_admin(token: str | None = Header(default=None)) -> None:
    if config.ADMIN_PASSWORD and token != config.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Sai token quản trị.")


def create_app() -> FastAPI:
    app = FastAPI(title="Chatbot Gmail Control Panel")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/status")
    def api_status():
        settings = storage.get_settings()
        state = storage.setup_state()
        running = bool(_bot_manager and _bot_manager.running)
        return {
            "bot": {
                "configured": state["bot_configured"],
                "username": settings.get("bot_username") or None,
                "running": running,
            },
            "llm": {
                "configured": state["llm_configured"],
                "provider": settings.get("llm_provider"),
                "model": settings.get("llm_model"),
                "base_url": settings.get("llm_base_url"),
            },
            "gcp": {"configured": state["gcp_configured"]},
            "gmail": {
                "configured": state["gmail_configured"],
                "email": settings.get("gmail_email"),
            },
            "ui_language": state["ui_language"],
            "all_done": state["all_done"],
        }

    @app.post("/api/setup/bot", dependencies=[Depends(_require_admin)])
    async def setup_bot(body: BotSetupBody):
        token = body.bot_token.strip()
        if not token:
            raise HTTPException(status_code=400, detail="Bot token trống.")
        username = ""
        warning = None
        bot = Bot(token=token)
        try:
            me = await bot.get_me()
            username = me.username or ""
        except TelegramUnauthorizedError:
            raise HTTPException(status_code=400, detail="Bot token không hợp lệ.")
        except Exception as exc:
            warning = f"Không kiểm tra được token qua mạng: {exc}"
        finally:
            await bot.session.close()

        storage.update_settings(bot_token=token, bot_username=username)
        running = False
        if _bot_manager is not None:
            try:
                running = await _bot_manager.restart()
            except Exception as exc:
                warning = f"Không khởi động được bot: {exc}"
        return {
            "ok": True,
            "username": username or None,
            "running": running,
            "warning": warning,
        }

    @app.post("/api/setup/language", dependencies=[Depends(_require_admin)])
    def setup_language(body: LanguageBody):
        storage.update_settings(ui_language=body.language)
        return {"ui_language": storage.get_settings().get("ui_language")}

    @app.post("/api/setup/llm", dependencies=[Depends(_require_admin)])
    def setup_llm(body: LlmSetupBody):
        storage.update_settings(
            llm_provider=body.provider or "openai",
            llm_model=body.model or "gpt-4o-mini",
            llm_api_key=body.api_key.strip(),
            llm_base_url=(body.base_url or "").strip(),
        )
        return storage.setup_state()

    @app.post("/api/setup/gcp", dependencies=[Depends(_require_admin)])
    def setup_gcp(body: GcpSetupBody):
        client_id, client_secret = body.client_id, body.client_secret
        if body.client_secret_json:
            try:
                parsed = gmail_client.parse_client_secret_json(body.client_secret_json)
            except (ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            client_id, client_secret = parsed["client_id"], parsed["client_secret"]
        if not (client_id and client_secret):
            raise HTTPException(status_code=400, detail="Thiếu client_id / client_secret.")
        storage.update_settings(
            gcp_client_id=client_id.strip(), gcp_client_secret=client_secret.strip()
        )
        return storage.setup_state()

    @app.post("/api/oauth/start")
    def oauth_start():
        client_id, _ = oauth.get_gcp_credentials()
        return {"url": oauth.build_auth_url(client_id, config.REDIRECT_URI)}

    @app.get("/oauth2callback")
    def oauth_callback(code: str | None = Query(default=None), error: str | None = Query(default=None)):
        return oauth.finalize_oauth(code, error)

    assets_dir = config.FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    index_file = config.FRONTEND_DIST / "index.html"

    @app.get("/", include_in_schema=False)
    def root(code: str | None = Query(default=None), error: str | None = Query(default=None)):
        if code or error:
            return oauth.finalize_oauth(code, error)
        if index_file.is_file():
            return FileResponse(str(index_file))
        return HTMLResponse(
            "<h3>Chatbot Gmail backend đang chạy.</h3>"
            "<p>Frontend chưa được build (chạy: npm run build trong frontend/).</p>"
        )

    return app


app = create_app()
