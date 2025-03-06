from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from bot.database import AsyncSessionLocal, Poem
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import StateFilter
import asyncio
from bot.yandexapi import get_poetry_idea
router = Router()

class PoemWriting(StatesGroup):
    rhyme_find = State()
    writing_poem = State()  # Состояние, когда пользователь пишет стих
    naming_poem = State()  # Новое состояние для ввода названия


# # Обработчик кнопки "Придумать идею"
@router.callback_query(F.data == 'idia_help')
async def generate_poetry_idea(callback: CallbackQuery):
    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
    await get_poetry_idea(callback)

@router.message(F.text == "Назад")
async def back_handler(message: Message, state: FSMContext):
    if await state.get_state():  # Проверяем, есть ли состояние
        await state.clear()
    await message.answer("Вы вернулись в главное меню.", reply_markup=kb.main)

@router.message(F.text == "Новый стих")
async def start_handler(message: Message, state: FSMContext):
    await message.answer("Создавай и созерцай!\nНет идей для стихотворения, попробуй её сгенерировать!", reply_markup=kb.inline_keyboard)

# Функция для сохранения стиха в базу данных
async def save_poem(user_id: int, title: str, text: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            poem = Poem(user_id=user_id, title=title, text=text)  # Добавляем title
            session.add(poem)

# Начало написания стиха
@router.callback_query(F.data == 'start_write')
async def start_write(callback: CallbackQuery, state: FSMContext):
    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
    await callback.answer(':･ﾟ✧:･.☽｡･ﾟ✧:･Взлетаем')
    await callback.message.answer(
        'Ты пишешь мне строчки, а я их запоминаю\n      ⸜(｡˃ ᵕ ˂ )⸝♡ \nКак закончишь, просто нажми "Сохранить"',
        reply_markup=kb.edit_poetry
    )
    await state.set_state(PoemWriting.writing_poem)  # Устанавливаем состояние "writing_poem"


@router.message(PoemWriting.writing_poem)
async def write_poem(message: Message, state: FSMContext):
    # Получаем данные из состояния в начале функции
    user_data = await state.get_data()
    poem_lines = user_data.get("poem_lines", [])
    if len(poem_lines) == 1:
        last_bot_message_id = user_data.get("last_bot_message_id")
        try:
            if last_bot_message_id:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")
    if message.text == "Сохранить":
        await message.delete()
        user_data = await state.get_data()
        poem_lines = user_data.get("poem_lines", [])
        poem_text = "\n".join(poem_lines)

        # Сохраняем текст в состояние и запрашиваем название
        await state.set_state(PoemWriting.naming_poem)  # Меняем состояние на ввод названия
        await state.update_data(poem_text=poem_text)
        sent_message = await message.answer("Стихотворение почти готово! Теперь придумай ему название ✨")
        await state.update_data(last_bot_message_id=sent_message.message_id)
        return
    if message.text == "Изменить строчку":
        await message.delete()
        user_data = await state.get_data()
        poem_lines = user_data.get("poem_lines", [])
        if not poem_lines:
            await message.answer("Ты ещё не написал ни одной строки!")
            await state.set_state(PoemWriting.writing_poem)
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
    if message.text == "Рифма к...":
        await message.delete()
        reply_markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Продолжить писать")]],  # Список кнопок, каждая кнопка в виде списка
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("К какому слову хочешь найти рифмы?",reply_markup = reply_markup)
        await state.set_state(PoemWriting.rhyme_find)
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
        poem_message = await message.answer(
            f"<pre>{formatted_poem}</pre>",
            parse_mode="HTML",
        )
        sent_message  = await message.answer("Продолжай писать!")
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.update_data(poem_message_id=poem_message.message_id)
    else:
        await message.bot.edit_message_text(
            f"<pre>{formatted_poem}</pre>",
            chat_id=message.chat.id,
            message_id=user_data['poem_message_id'],
            parse_mode="HTML",
        )
    await message.delete()

@router.callback_query(lambda c: c.data.startswith("data_conversayshn_line_"))
async def handle_data_conversayshn_line(callback: CallbackQuery):
    line_index = int(callback.data.split("_")[-1])
    buttons = [
        [InlineKeyboardButton(text= "Изменить", callback_data=f"data_edit_line_{line_index}"),InlineKeyboardButton(text= "Удалить", callback_data=f"data_delete_line_{line_index}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"Что хочешь сделать?",
        reply_markup=keyboard
    )
@router.callback_query(lambda c: c.data.startswith("data_edit_line_") or c.data.startswith("data_delete_line_"))
async def handle_edit_or_delete_line(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор строки для редактирования или удаления."""
    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
    user_data = await state.get_data()
    poem_lines = user_data.get("poem_lines", [])

    # Определяем действие (редактирование или удаление) и индекс строки
    action, line_index = callback.data.split("_")[1], int(callback.data.split("_")[-1])

    if not (0 <= line_index < len(poem_lines)):
        await callback.answer("Ошибка: строка не найдена!", show_alert=True)
        await asyncio.sleep(5)
        return

    if action == "edit":
        # Пользователь выбрал редактирование
        await state.update_data(editing_line=line_index)  # Запоминаем индекс строки
        sent_message = await callback.message.answer(
            f"Ты выбрал строку:\n\n<pre>{poem_lines[line_index]}</pre>\n\nВведи новый текст строки:",
            parse_mode="HTML"
        )
        await state.update_data(last_bot_message_id=sent_message.message_id)
        await state.set_state("editing_line")

    elif action == "delete":
        # Пользователь выбрал удаление
        deleted_line = poem_lines.pop(line_index)  # Удаляем строку
        await state.update_data(poem_lines=poem_lines)  # Обновляем state

        formatted_poem = "\n".join(poem_lines) or "Стих пуст."

        # Обновляем сообщение со стихотворением (если оно уже есть)
        if "poem_message_id" in user_data:
            await callback.message.bot.edit_message_text(
                f"<pre>{formatted_poem}</pre>",
                chat_id=callback.message.chat.id,
                message_id=user_data["poem_message_id"],
                parse_mode="HTML"
            )
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)
        await callback.answer(f"Строка удалена:\n«{deleted_line}» ❌", show_alert=False)
        await state.set_state(PoemWriting.writing_poem)

@router.message(StateFilter("editing_line"))
async def process_editing_line(message: Message, state: FSMContext):
    """Обрабатывает ввод новой строки при редактировании."""
    user_data = await state.get_data()
    last_bot_message_id = user_data.get("last_bot_message_id")
    await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
    user_data = await state.get_data()
    poem_lines = user_data.get("poem_lines", [])
    editing_line = user_data.get("editing_line")

    if editing_line is None or not (0 <= editing_line < len(poem_lines)):
        await message.answer("Ошибка: невозможно изменить строку!")
        return

    # Заменяем старую строку новой
    old_line = poem_lines[editing_line]
    poem_lines[editing_line] = message.text
    await state.update_data(poem_lines=poem_lines, editing_line=None)

    formatted_poem = "\n".join(poem_lines)

    # Обновляем сообщение со стихотворением (если оно уже отправлено)
    if "poem_message_id" in user_data:
        try:
            await message.bot.edit_message_text(
                f"<pre>{formatted_poem}</pre>",
                chat_id=message.chat.id,
                message_id=user_data["poem_message_id"],
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка обновления сообщения: {e}")
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    # Выходим из состояния редактирования
    await state.update_data(editing_line=None)
    await state.set_state(PoemWriting.writing_poem)
@router.message(PoemWriting.naming_poem)
async def get_poem_title(message: Message, state: FSMContext):
    await message.delete()
    user_data = await state.get_data()
    last_bot_message_id = user_data.get("last_bot_message_id")
    await message.bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message_id)
    user_data = await state.get_data()
    poem_text = user_data.get("poem_text", "Без текста")  # Получаем текст стиха

    title = message.text  # Сохраняем название

    # Сохраняем в базу данных
    await save_poem(user_id=message.from_user.id, title=title, text=poem_text)

    await message.answer(f'Стих "{title}" сохранён!\n     ٩(^ᗜ^ )و ´-', reply_markup=kb.main)

    # Выход из состояния
    await state.clear()





