import asyncio
from aiogram import Bot, Dispatcher
from config import config
from bot.handlers import rt

BOT_TOKEN = str(config.BOT_TOKEN)

dp = Dispatcher()
dp.include_router(rt)

async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())