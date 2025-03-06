import asyncio
from config.config import TOKEN
from bot.database import init_db
from aiogram import Bot, Dispatcher, F
from bot.handlers.handler import router
from bot.handlers.start import router_start
from bot.handlers.save_poetry import router_write
from bot.handlers.all_poetry import router_all_poetry
from bot.handlers.edit_poetry import router_edit_poetry
from bot.handlers.rhyme_find import rhyme_router
from bot.Admin.Poem_view import admin_router
from aiogram.types import ReactionTypeEmoji,Message


bot = Bot(token = TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    dp.include_router(router_start)
    dp.include_router(router_write)
    dp.include_router(router_all_poetry)
    dp.include_router(router_edit_poetry)
    dp.include_router(rhyme_router)
    dp.include_router(admin_router)
    await init_db()  # Создаём таблицы в базе
    await dp.start_polling(bot)


@dp.message(F.sticker)
async def react_to_sticker(message: Message):
    await bot.set_message_reaction(  # Используем bot, а не router!
        chat_id=message.chat.id,
        message_id=message.message_id,
        reaction=[ReactionTypeEmoji(emoji="🍓")]  # Реакция на стикер
    )
if __name__ == '__main__':
    asyncio.run(main())