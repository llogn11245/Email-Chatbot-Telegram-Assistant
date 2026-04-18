from aiogram import Router, types
from aiogram.filters import Command

rt = Router()

@rt.message(Command("introduction"))
async def start_command(message: types.Message):
    await message.reply(text = 'Hello! I am your friendly Telegram bot. How can I assist you today?')