import asyncio

from aiogram import Bot, Dispatcher

from app.core import storage
from app.telegram.handlers import rt


class BotManager:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._token: str | None = None
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def username(self) -> str | None:
        return storage.get_settings().get("bot_username") or None

    async def start(self) -> bool:
        async with self._lock:
            token = storage.get_settings().get("bot_token")
            if not token:
                return False
            if self.running and self._token == token:
                return True
            await self._stop_locked()
            self._token = token
            self._task = asyncio.create_task(self._poll(token))
            return True

    async def _poll(self, token: str) -> None:
        bot = Bot(token=token)
        dispatcher = Dispatcher()
        dispatcher.include_router(rt)
        try:
            await dispatcher.start_polling(bot)
        finally:
            await bot.session.close()

    async def _stop_locked(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def stop(self) -> None:
        async with self._lock:
            await self._stop_locked()

    async def restart(self) -> bool:
        await self.stop()
        return await self.start()
