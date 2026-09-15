import asyncio

import uvicorn

from backend import config
from backend.bot.manager import BotManager
from backend.web import webapp


async def _run_web() -> None:
    server = uvicorn.Server(
        uvicorn.Config(
            webapp.app,
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            log_level="info",
            access_log=False,
        )
    )
    await server.serve()


async def main() -> None:
    mode = config.RUN_MODE
    manager = BotManager()
    tasks = []
    if mode in ("both", "web"):
        tasks.append(_run_web())
    if mode in ("both", "bot"):
        webapp.set_bot_manager(manager)
        await manager.start()
    if not tasks:
        print("Không có gì để chạy (RUN_MODE=bot và chưa cấu hình web).")
        return
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
