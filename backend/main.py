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
    manager = BotManager()
    tasks = []
    tasks.append(_run_web())
    webapp.set_bot_manager(manager)
    await manager.start()
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
