from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, func, desc
from bot.database import AsyncSessionLocal, Poem
from bot.handlers.save_poetry import get_poems_with_pagination, send_poem_with_buttons
from aiogram.fsm.context import FSMContext

router_all_poetry = Router()

@router_all_poetry.message(F.text == "Все стихи")
async def profile_handler(message: Message):
    """Выводит количество стихов и их список с кнопками."""
    async with AsyncSessionLocal() as session:
        # Получаем общее количество стихов пользователя
        total_count = await session.execute(
            select(func.count(Poem.id)).where(Poem.user_id == message.from_user.id)
        )
        total_poems = total_count.scalar()

        # Получаем список всех стихотворений с ID и названием
        result = await session.execute(
            select(Poem.id, Poem.title)
            .where(Poem.user_id == message.from_user.id)
            .order_by(Poem.created_at.desc())
        )
        poems = result.all()

    if total_poems > 0:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{i + 1}. {title}", callback_data=f"poem_{poem_id}")]
                for i, (poem_id, title) in enumerate(poems)
            ]
        )

        await message.answer(
            f"<b>Твой профиль</b>\n\n"
            f"<b>Всего стихов:</b> {total_poems}\n\n"
            f"Выбери стих, чтобы посмотреть его:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await message.answer("Ты ещё не сохранил ни одного стиха. Начни творить! ✨")

@router_all_poetry.callback_query(lambda c: c.data.startswith("poem_"))
async def poem_callback(callback: CallbackQuery, state = FSMContext):
    # Извлекаем ID стихотворения из callback_data
    action, poem_id = callback.data.split("_")
    poem_id = int(poem_id)

    # Получаем стихотворение по ID
    poem, total, poem_ids = await get_poems_with_pagination(callback.from_user.id, poem_id=poem_id)  # Пагинацию по ID

    # Если стихотворение не найдено
    if poem is None or poem.id != poem_id:
        await callback.answer("Ошибка: стихотворение не найдено или ID неверен!")
        return

    # Удаляем старое сообщение, если оно ещё существует
    try:
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение: {e}")

    # Отправляем новое сообщение с текстом стиха
    await send_poem_with_buttons(callback.message, poem, total=total, poem_id=poem_id, poem_ids=poem_ids,state=state)
