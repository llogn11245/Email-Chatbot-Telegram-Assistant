import asyncio
import socket
import threading
import time

import uvicorn

from backend import config
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
    """Chạy web server + Telegram bot trong một event loop ở thread nền."""

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
