import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "🏠 هومن ریل‌استیت CRM\n\n"
        "بات با موفقیت فعال شد."
    )

async def main():
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
