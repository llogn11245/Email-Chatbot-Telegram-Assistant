import asyncio
import logging
import sys

import uvicorn

from backend import config
from backend.bot.manager import BotManager
from backend.observability import record_event, setup_logging
from backend.web import webapp

_log = logging.getLogger("app.main")


def _install_global_handlers() -> None:
    def _excepthook(exc_type, exc_value, exc_tb):
        record_event("ERROR", "main", f"uncaught: {exc_value}", exc=exc_value)
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    def _loop_handler(loop, context):
        exc = context.get("exception")
        record_event("ERROR", "main", f"loop error: {context.get('message')}", exc=exc)

    try:
        asyncio.get_event_loop().set_exception_handler(_loop_handler)
    except RuntimeError:
        pass


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
    setup_logging()
    _install_global_handlers()
    _log.info("starting web + bot (web %s:%s)", config.WEB_HOST, config.WEB_PORT)

    manager = BotManager()
    tasks = [_run_web()]
    webapp.set_bot_manager(manager)
    await manager.start()
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
