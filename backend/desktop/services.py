import asyncio
import concurrent.futures
import socket
import threading
import time

import uvicorn

from backend import config, storage
from backend.bot.manager import BotManager
from backend.observability import record_event
from backend.web import webapp


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    connect_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    try:
        with socket.create_connection((connect_host, port), timeout=timeout):
            return True
    except OSError:
        return False


class ServiceRunner:
    """Chạy web server (cho OAuth callback) + Telegram bot trong một event loop ở thread nền."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port or config.WEB_PORT
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: uvicorn.Server | None = None
        self._manager: BotManager | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self, wait: bool = True) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="services", daemon=True)
        self._thread.start()
        if wait:
            self.wait_until_ready()

    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _port_open(config.WEB_HOST, self.port):
                return True
            time.sleep(0.2)
        return False

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()

    async def _main(self) -> None:
        self._manager = BotManager()
        webapp.set_bot_manager(self._manager)
        self._server = uvicorn.Server(
            uvicorn.Config(
                webapp.app,
                host=config.WEB_HOST,
                port=self.port,
                log_level="warning",
                access_log=False,
            )
        )
        try:
            await self._manager.start()
        except Exception as exc:
            record_event("ERROR", "services", f"bot start failed: {exc}", exc=exc)
        try:
            await self._server.serve()
        finally:
            try:
                await self._manager.stop()
            except Exception:
                pass

    def stop(self) -> None:
        if self._server is not None and self._loop is not None:
            self._loop.call_soon_threadsafe(setattr, self._server, "should_exit", True)
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    # -- API cho GUI -------------------------------------------------------
    def submit(self, coro, timeout: float | None = 30.0):
        if self._loop is None:
            raise RuntimeError("services chưa chạy")
        future: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout) if timeout else future

    def is_bot_running(self) -> bool:
        try:
            return bool(self._manager and self._manager.running)
        except Exception:
            return False

    def set_bot_token(self, token: str) -> dict:
        return self.submit(self._set_bot_token(token), timeout=30)

    async def _set_bot_token(self, token: str) -> dict:
        from aiogram import Bot
        from aiogram.exceptions import TelegramUnauthorizedError

        token = (token or "").strip()
        if not token:
            raise ValueError("Bot token trống.")

        username = ""
        warning = None
        bot = Bot(token=token)
        try:
            me = await bot.get_me()
            username = me.username or ""
        except TelegramUnauthorizedError as exc:
            raise ValueError("Bot token không hợp lệ.") from exc
        except Exception as exc:
            warning = f"Không kiểm tra được token qua mạng: {exc}"
        finally:
            await bot.session.close()

        storage.update_settings(bot_token=token, bot_username=username)
        running = False
        if self._manager is not None:
            try:
                running = await self._manager.restart()
            except Exception as exc:
                warning = f"Không khởi động được bot: {exc}"
        return {"username": username, "running": running, "warning": warning}
