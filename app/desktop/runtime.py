import asyncio
import concurrent.futures
import threading

from app.core import storage
from app.core.observability import record_event
from app.telegram.manager import BotManager


class Runtime:
    """Chạy Telegram bot trong một event loop ở thread nền; cung cấp API thread-safe cho GUI."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._manager: BotManager | None = None
        self._stop_event: asyncio.Event | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="runtime", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        finally:
            self._loop.close()

    async def _main(self) -> None:
        self._manager = BotManager()
        self._stop_event = asyncio.Event()
        try:
            await self._manager.start()
        except Exception as exc:
            record_event("ERROR", "runtime", f"bot start failed: {exc}", exc=exc)
        await self._stop_event.wait()

    def stop(self) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def submit(self, coro, timeout: float | None = 30.0):
        if self._loop is None:
            raise RuntimeError("runtime chưa chạy")
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
