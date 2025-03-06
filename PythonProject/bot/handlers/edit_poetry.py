from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, KeyboardButton, ReplyKeyboardMarkup
from sqlalchemy import select, desc
from bot.database import Poem, AsyncSessionLocal
from bot.handlers.save_poetry import get_poems_with_pagination, send_poem_with_buttons
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import keyboards as kb
from aiogram.exceptions import TelegramBadRequest
import asyncio
class PoemEditing(StatesGroup):
    editing_poem = State()  # State for editing a poem
    new_line_poem = State()
    naming_poem = State()
    window = State()
    find_rhyme = State()
router_edit_poetry = Router()

@router_edit_poetry.callback_query(lambda c: c.data.startswith('remove_poetry_'))
async def remove_poetry(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    try:
        await callback.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest as e:
        print(f"Ошибка при удалении сообщения: {e}")
        # Здесь можно добавить логику для повторных попыток или другую обработку ошибок
    _, _, poem_id = callback.data.split("_")
    poem_id = int(poem_id)
    # Открываем асинхронную сессию
    async with AsyncSessionLocal() as session:
        # Выполняем запрос для нахождения стиха по id
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalars().first()

        # Если стих найден, удаляем его
        if poem:
            await session.delete(poem)
            await session.commit()
            await callback.answer("Стих удалён успешно!")
        else:
            await callback.answer("Стих с таким ID не найден.")

# ВЫБОР СТИХА ДЛЯ РЕДАКТИРОВАНИЯ
@router_edit_poetry.callback_query(lambda c: c.data.startswith('edit_poetry_'))
async def edit_poetry(callback: CallbackQuery):
    _, _, poem_id = callback.data.split("_")
    poem_id = int(poem_id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()
        poem_lines = poem.text.split("\n")

        buttons = [
            [InlineKeyboardButton(text=f"{i + 1}. {line[:40]}", callback_data=f"edit_line_{poem_id}_{i}")]
            for i, line in enumerate(poem_lines)
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            f"Вы выбрали стих:\n\n<pre>{poem.text}</pre>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer("Выберите строку для редактирования или удаления.")

# ВЫБОР СТРОКИ ДЛЯ РЕДАКТИРОВАНИЯ/УДАЛЕНИЯ
@router_edit_poetry.callback_query(lambda c: c.data.startswith("edit_line_"))
async def edit_line(callback: CallbackQuery):
    _, _, poem_id, line_index = callback.data.split("_")
    poem_id, line_index = int(poem_id), int(line_index)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if not poem:
            await callback.answer("Ошибка: стихотворение не найдено.")
            return

        poem_lines = poem.text.split("\n")

        if not (0 <= line_index < len(poem_lines)):
            await callback.answer("Ошибка: строка не найдена.")
            return

        selected_line = poem_lines[line_index]

        buttons = [
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{poem_id}_{line_index}")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_{poem_id}_{line_index}")],
            [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"cancel_edit_{poem_id}")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            f"Вы выбрали строку:\n\n<pre>{selected_line}</pre>",
            parse_mode="HTML",
            reply_markup=keyboard
        )

# РЕДАКТИРОВАНИЕ СТРОКИ
@router_edit_poetry.callback_query(lambda c: c.data.startswith("edit_"))
async def start_editing(callback: CallbackQuery, state: FSMContext):
    _, poem_id, line_index = callback.data.split("_")

    # Проверяем, что данные в правильном формате
    if not poem_id.isdigit() or not line_index.isdigit():
        await callback.answer("Ошибка: некорректный формат данных.")
        return

    poem_id, line_index = int(poem_id), int(line_index)

    # Получаем стихотворение из базы
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if not poem:
            await callback.answer("Ошибка: стихотворение не найдено.")
            return

        poem_lines = poem.text.split("\n")

        if not (0 <= line_index < len(poem_lines)):
            await callback.answer("Ошибка: строка не найдена.")
            return

        selected_line = poem_lines[line_index]

        cancel_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True,  # Делает клавиатуру компактнее
            one_time_keyboard=True  # Клавиатура исчезает после нажатия
        )
        # Отправляем сообщение с выбранной строкой для редактирования
        await callback.message.answer(
            f"Выбрана строка для редактирования:\n\n<pre>{selected_line}</pre>\n\n"
            f"Отправьте новую версию строки или нажмите \"Отмена\".",
            parse_mode="HTML",
            reply_markup=cancel_keyboard
        )

        # Сохраняем poem_id и line_index в состоянии
        await state.update_data(poem_id=poem_id, line_index=line_index)
        await state.set_state(PoemEditing.editing_poem)  # Устанавливаем состояние редактирования


# ОБРАБОТКА НОВОЙ СТРОКИ
@router_edit_poetry.message(PoemEditing.editing_poem)
async def edit_poem_line(message: Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await message.answer("❌ Редактирование отменено.", reply_markup=kb.main)
        await state.clear()  # Очищаем состояние
        return

    user_data = await state.get_data()
    poem_id = user_data.get("poem_id")
    line_index = user_data.get("line_index")

    if poem_id is None or line_index is None:
        await message.answer("Ошибка: данные о стихотворении потеряны.", reply_markup=kb.main)
        await state.clear()  # Очищаем состояние
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if not poem:
            await message.answer("Ошибка: стихотворение не найдено.", reply_markup=kb.main)
            await state.clear()  # Очищаем состояние
            return

        poem_lines = poem.text.split("\n")

        if not (0 <= line_index < len(poem_lines)):
            await message.answer("Ошибка: строка не найдена.", reply_markup=kb.main)
            await state.clear()  # Очищаем состояние
            return

        # Обновляем текст
        poem_lines[line_index] = message.text
        poem.text = "\n".join(poem_lines)
        await message.answer(f"Строка изменена",eply_markup=kb.main)
        poem_zxc, total, poem_ids = await get_poems_with_pagination(message.from_user.id, poem_id=poem_id)
        await send_poem_with_buttons(message, poem, total=total, poem_id=poem_id, poem_ids=poem_ids,state=state)
        await session.commit()

    await state.clear()

@router_edit_poetry.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_line(callback: CallbackQuery):
    _, poem_id, line_index = callback.data.split("_")
    line_index = int(line_index)
    poem_id = int(poem_id)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if not poem:
            await callback.answer("Ошибка: стихотворение не найдено.")
            return

        poem_lines = poem.text.split("\n")

        if 0 <= line_index < len(poem_lines):
            await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)

            buttons = [
                [InlineKeyboardButton(text="❌ Да, удалить", callback_data=f"confirm_delete_{poem_id}_{line_index}")],
                [InlineKeyboardButton(text="🔙 Отмена", callback_data=f"cancel_edit_{poem_id}")]
            ]
            keyboard_dec = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.answer(
                f"⚠️ Вы уверены, что хотите удалить строку:\n\n<pre>{poem_lines[line_index]}</pre>",
                parse_mode="HTML",
                reply_markup=keyboard_dec
            )
        else:
            await callback.answer("Ошибка: строка не найдена.")

@router_edit_poetry.callback_query(lambda c: c.data.startswith("confirm_delete"))
async def confirm_delete(callback: CallbackQuery, state: FSMContext):
    _,_, poem_id, line_index = callback.data.split("_")
    poem_id, line_index = int(poem_id), int(line_index)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if not poem:
            await callback.answer("Ошибка: стихотворение не найдено.")
            return

        poem_lines = poem.text.split("\n")

        if 0 <= line_index < len(poem_lines):
            deleted_line = poem_lines.pop(line_index)
            poem.text = "\n".join(poem_lines)
            await session.commit()
            await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
            await callback.answer(
                f"✅ Строка удалена")
            poem, total, poem_ids = await get_poems_with_pagination(callback.from_user.id, poem_id=poem_id)

            if poem is None:
                await callback.answer("Ошибка: стихотворение не найдено!")
                return

            # Отправляем новое сообщение с текстом стиха
            await send_poem_with_buttons(callback.message, poem, total=total, poem_id=poem_id, poem_ids=poem_ids,state=state)
        else:
            await callback.answer("Ошибка: строка не найдена.")

@router_edit_poetry.callback_query(lambda c: c.data.startswith("cancel_edit"))
async def cancel_edit(callback: CallbackQuery, state =FSMContext):
    _, _, poem_id= callback.data.split("_")
    poem_id = int(poem_id)
    poem, total, poem_ids = await get_poems_with_pagination(callback.from_user.id, poem_id=poem_id)
    await callback.answer("❌ Действие отменено.")
    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)

    if poem is None:
        await callback.answer("Ошибка: стихотворение не найдено!")
        return

    # Отправляем новое сообщение с текстом стиха
    await send_poem_with_buttons(callback.message, poem, total=total, poem_id=poem_id, poem_ids=poem_ids,state=state)


@router_edit_poetry.callback_query(lambda c: c.data.startswith("new_line"))
async def new_back_line(callback: CallbackQuery, state: FSMContext):
    _, _, poem_id = callback.data.split("_")
    poem_id = int(poem_id)
    await state.update_data(poem_id = poem_id)
    # Получаем данные о стихотворении из базы данных
    async with AsyncSessionLocal() as session:
        # Выполняем запрос для поиска стихотворения по его ID
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()
    # Проверяем, найдено ли стихотворение
    if poem is None:
        await callback.answer("Стихотворение не найдено!", show_alert=True)
        return
    # Извлекаем строки стихотворения
    poem_lines = poem.text.split("\n")  # или используйте другую логику для извлечения строк из стихотворения
    # Обновляем данные в FSM
    await state.update_data(poem_lines=poem_lines)
    # Ответ пользователю
    sent_message = await callback.message.answer(f"Вы можете продолжить стихотворение!")
    await state.update_data(last_bot_message_id=sent_message.message_id)
    await state.set_state(PoemEditing.new_line_poem)

@router_edit_poetry.message(PoemEditing.new_line_poem)
async def write_poem(message: Message, state: FSMContext):
    # Получаем данные из состояния в начале функции
    user_data = await state.get_data()
    poem_lines = user_data.get("poem_lines", [])
    poem_id = user_data.get("poem_id")
    poem_id = int(poem_id)
    title = await get_poem_title(poem_id)
    if message.text == "Сохранить":
        await message.delete()
        user_data = await state.get_data()
        poem_lines = user_data.get("poem_lines", [])
        poem_text = "\n".join(poem_lines)
        await state.update_data(poem_text=poem_text)
        last_bot_message_id = user_data.get("last_bot_message_id")
        await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
        sent_message = await message.answer(f"Введите новое название стихотворения.\nТвое старое название:\n<pre>{title}</pre>",
            parse_mode="HTML",reply_markup=kb.edit_poetry)
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state(PoemEditing.naming_poem)
        return
    if message.text == "Изменить строчку":
        await message.delete()
        user_data = await state.get_data()
        poem_lines = user_data.get("poem_lines", [])
        if not poem_lines:
            await message.answer("Ты ещё не написал ни одной строки!")
            await state.set_state(PoemEditing.new_line_poem)
            return
        buttons = [
            [InlineKeyboardButton(text=f"{i + 1}. {line[:40]}", callback_data=f"data_conversayshn_line_{i}")]
            for i, line in enumerate(poem_lines)
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"Выберите строку для редактирования или удаления:",
            reply_markup=keyboard
        )
        return
    # Если пользователь заменяет строку
    # Если это редактирование
    if "editing_line" in user_data:
        editing_index = user_data["editing_line"]
        if 0 <= editing_index < len(poem_lines):
            poem_lines[editing_index] = message.text
            await state.update_data(poem_lines=poem_lines)
        await state.update_data(editing_line=None)
    else:
        # Добавляем новую строку, если не редактируем
        poem_lines.append(message.text)
        await state.update_data(poem_lines=poem_lines)
    formatted_poem = "\n".join(poem_lines)

    # Если это первое сообщение, отправляем новое. Если сообщение уже существует, редактируем его.
    if 'poem_message_id' not in user_data:
        sent_message = await message.answer(
            'Как закончишь, нажми "Сохранить"',
            reply_markup=kb.edit_poetry
        )
        last_bot_message_id = user_data.get("last_bot_message_id")
        try:
            if last_bot_message_id:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")
        await state.update_data(last_bot_message_id=sent_message.message_id)
        poem_message = await message.answer(
            f"<pre>{formatted_poem}</pre>",
            parse_mode="HTML"
        )
        await state.update_data(poem_message_id=poem_message.message_id)
    else:
        await message.bot.edit_message_text(
            f"<pre>{formatted_poem}</pre>",
            chat_id=message.chat.id,
            message_id=user_data['poem_message_id'],
            parse_mode="HTML",
        )
    await message.delete()
async def get_poem_title(poem_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Poem.title).where(Poem.id == poem_id)
        )
        title = result.scalar_one_or_none()  # Получаем название или None
        return title

@router_edit_poetry.message(PoemEditing.naming_poem)
async def confirm_save_poem(message: Message, state: FSMContext):
    user_data = await state.get_data()
    poem_text = user_data.get("poem_text")
    poem_id = user_data.get("poem_id")
    if not poem_text or not poem_id:
        await message.answer("Ошибка: не найден текст стихотворения или его ID.")
        return
    title = message.text  # Берем введенное название
    await update_poem(poem_id=poem_id, title=title, text=poem_text)
    await message.answer(f'Стих "{title}" обновлён! ✨', reply_markup=kb.main)
    await message.delete()
    last_bot_message_id = user_data.get("last_bot_message_id")
    await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
    await message.bot.delete_message(message.message.chat.id, message.message.message_id)
    await state.clear()  # Сбрасываем состояние

async def update_poem(poem_id: int, title: str, text: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Poem).where(Poem.id == poem_id))
        poem = result.scalar_one_or_none()

        if poem:
            poem.title = title
            poem.text = text
            await session.commit()
