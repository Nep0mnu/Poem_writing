from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.future import select
from sqlalchemy import desc, func
from bot.database import AsyncSessionLocal, Poem
from aiogram.fsm.context import FSMContext

router_write = Router()


async def get_poems_with_pagination(user_id: int, poem_id: int):
    async with AsyncSessionLocal() as session:
        try:
            # Находим стихотворение по ID
            result = await session.execute(
                select(Poem).where(Poem.user_id == user_id, Poem.id == poem_id)
            )
            poem = result.scalar_one_or_none()

            if poem is None:
                return None, 0, []  # Если стихотворение не найдено

            # Считаем общее количество стихотворений
            total_result = await session.execute(
                select(func.count(Poem.id)).where(Poem.user_id == user_id)
            )
            total = total_result.scalar()

            # Возвращаем стих, общее количество и список всех ID стихотворений
            result_ids = await session.execute(
                select(Poem.id).where(Poem.user_id == user_id).order_by(desc(Poem.created_at))
            )
            poem_ids = [row[0] for row in result_ids.all()]

            return poem, total, poem_ids  # Возвращаем стих, общее количество и все ID стихотворений

        except Exception as e:
            print(f"Ошибка при получении стихов: {e}")
            return None, 0, []


@router_write.message(F.text == "Последний стих")
async def my_poems_handler(message: Message,state:FSMContext):
    """Выводит самое старое стихотворение пользователя."""
    async with AsyncSessionLocal() as session:
        # Получаем ID самого первого стихотворения (по дате создания)
        result = await session.execute(
            select(Poem.id)
            .where(Poem.user_id == message.from_user.id)
            .order_by(Poem.created_at)
            .limit(1)
        )
        first_poem_id = result.scalar_one_or_none()

    if first_poem_id is None:
        await message.answer("У тебя пока нет сохранённых стихов. Начни творить! ✨")
        return

    # Получаем полное стихотворение
    poem, total, poem_ids = await get_poems_with_pagination(message.from_user.id, poem_id=first_poem_id)

    if poem:
        await send_poem_with_buttons(message, poem, poem_id=poem.id, total=total, poem_ids=poem_ids,state=state)


async def send_poem_with_buttons(message: Message, poem: Poem, poem_id: int, total: int, poem_ids: list,state: FSMContext):
    width = 40  # Фиксированная ширина
    poem_text = poem.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    formatted_text = "\n".join(line.ljust(width) for line in poem_text.split("\n"))

    title_padding = int((width - len(poem.title)))  # Считаем количество пробелов слева и справа
    centered_title = f"<b>{' ' * title_padding}{poem.title}{' ' * title_padding}</b>"

    # Формируем кнопки для пагинации
    buttons = []
    current_index = poem_ids.index(poem_id) if poem_id in poem_ids else -1

    if current_index > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{poem_ids[current_index - 1]}"))
    if current_index < total - 1:
        buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"next_{poem_ids[current_index + 1]}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        buttons,
        [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_poetry_{poem_id}")],
        [InlineKeyboardButton(text="Дополнить", callback_data=f"new_line_{poem_id}")],
        [InlineKeyboardButton(text="Удалить", callback_data=f"remove_poetry_{poem_id}")]
    ])

    sent_message = await message.answer(
        f"{centered_title}\n\n<pre>{formatted_text}</pre>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.update_data(chat_id=sent_message.chat.id, message_id=sent_message.message_id)



@router_write.callback_query(lambda c: c.data.startswith("prev_") or c.data.startswith("next_"))
async def pagination_callback(callback: CallbackQuery, state: FSMContext):
    action, poem_id = callback.data.split("_")
    poem_id = int(poem_id)  # Преобразуем в число

    poem, total, poem_ids = await get_poems_with_pagination(callback.from_user.id, poem_id=poem_id)

    if poem:
        buttons = []
        current_index = poem_ids.index(poem_id)

        if current_index > 0:
            buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{poem_ids[current_index - 1]}"))
        if current_index < total - 1:
            buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"next_{poem_ids[current_index + 1]}"))

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text="Редактировать", callback_data=f"edit_poetry_{poem_id}")],
            [InlineKeyboardButton(text="Дополнить", callback_data=f"new_line_{poem_id}")],
            [InlineKeyboardButton(text="Удалить", callback_data=f"remove_poetry_{poem_id}")]
        ])

        width = 40  # Фиксированная ширина

        poem_text = poem.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        formatted_text = "\n".join(line.ljust(width) for line in poem_text.split("\n"))

        title_padding = int((width - len(poem.title)))  # Считаем количество пробелов слева и справа
        centered_title = f"<b>{' ' * title_padding}{poem.title}{' ' * title_padding}</b>"

        await callback.message.edit_text(
            f"<b>{centered_title}</b>\n\n<pre>{formatted_text}</pre>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.update_data(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    await callback.answer()


