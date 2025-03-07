from config.bot import ADMIN_IDS
from aiogram import Router, types, F
from aiogram.types import Message
from keyboards import admin_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.database import AsyncSessionLocal, Poem, User
from sqlalchemy.future import select
from aiogram.filters import Command

admin_router = Router()

@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.reply("Добро пожаловать в админ-панель!",reply_markup = admin_keyboard)
    else:
        await message.reply("У вас нет доступа к этой команде.")

@admin_router.message(F.text == "Пользователи")
async def view_tg_name(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("У вас нет доступа к этой команде.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await message.reply("Нет зарегистрированных пользователей.")
        return

    keyboard = InlineKeyboardBuilder()
    for user in users:
        keyboard.button(text=user.username, callback_data=f"adminuser_{user.id}")

    keyboard.adjust(2)  # По 2 кнопки в ряд
    await message.reply("Выберите пользователя:", reply_markup=keyboard.as_markup())

@admin_router.callback_query(F.data.startswith("adminuser_"))
async def show_user_poems(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.user_id == user_id))
        poems = result.scalars().all()

    if not poems:
        await callback.message.edit_text("У этого пользователя нет сохраненных стихов.")
        return

    keyboard = InlineKeyboardBuilder()
    for poem in poems:
        keyboard.button(text=poem.title, callback_data=f"adminpoem_{poem.id}")

    keyboard.adjust(1)  # По 1 кнопке в ряд
    await callback.message.edit_text("Выберите стих:", reply_markup=keyboard.as_markup())

@admin_router.callback_query(F.data.startswith("adminpoem_"))
async def show_poem(callback: types.CallbackQuery):
    poem_id = int(callback.data.split("_")[1])

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar()

    if not poem:
        await callback.answer("Стихотворение не найдено.", show_alert=True)
        return

    # Получаем ID всех стихов пользователя
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem.id).where(Poem.user_id == poem.user_id))
        poem_ids = [row[0] for row in result.all()]

    # Определяем индексы для кнопок "Вперед" и "Назад"
    index = poem_ids.index(poem_id)
    prev_poem_id = poem_ids[index - 1] if index > 0 else None
    next_poem_id = poem_ids[index + 1] if index < len(poem_ids) - 1 else None

    # Создаём кнопки
    keyboard = InlineKeyboardBuilder()
    if prev_poem_id:
        keyboard.button(text="⬅ Назад", callback_data=f"adminpoem_{prev_poem_id}")
    if next_poem_id:
        keyboard.button(text="Вперед ➡", callback_data=f"adminpoem_{next_poem_id}")

    keyboard.adjust(2)  # Две кнопки в строке

    await callback.message.edit_text(
        f"📜 *{poem.title}*\n\n{poem.text}",
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

