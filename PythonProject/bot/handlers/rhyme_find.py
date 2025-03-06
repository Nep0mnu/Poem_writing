import logging
import aiohttp
from bs4 import BeautifulSoup
import re
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.handlers.handler import PoemWriting  # Импортируем состояния
import keyboards as kb
import asyncio

rhyme_router = Router()


# Функция для проверки, русское ли слово
def is_russian_word(word: str) -> bool:
    return bool(re.match(r"^[а-яА-ЯёЁ]+$", word))


# Функция для создания кнопок пагинации
def get_pagination_keyboard(page: int, total_pages: int):
    keyboard = InlineKeyboardBuilder()

    if page > 0:
        keyboard.button(text="⬅️ Назад", callback_data=f"rhyme_page_{page - 1}")
    if page < total_pages - 1:
        keyboard.button(text="Вперёд ➡️", callback_data=f"rhyme_page_{page + 1}")

    keyboard.adjust(2)  # Располагаем кнопки в один ряд
    return keyboard.as_markup()


# Обработчик поиска рифм
@rhyme_router.message(PoemWriting.rhyme_find)
async def find_rhyme(message: types.Message, state: FSMContext):
    await message.delete()
    if message.text == "Продолжить писать":
        data = await state.get_data()
        # Получаем chat_id и message_id
        chat_id = data.get("chat_id")
        message_id = data.get("message_id")
        if chat_id and message_id:
            await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await message.answer("Я запоминаю...",reply_markup = kb.edit_poetry )
        await state.set_state(PoemWriting.writing_poem)
        return
    word = message.text.strip()
    # Проверяем, русское ли слово
    if not is_russian_word(word):
        await message.answer("Введите слово на русском языке.")
        await asyncio.sleep(5)
        await message.delete()
        return

    url = f"https://rifmovka.ru/rifma/{word}"
    logging.info(f"Поиск рифм для слова: {word}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    rhyme_blocks = soup.find_all("ul")
                    rhymes = []
                    for block in rhyme_blocks:
                        for li in block.find_all("li"):
                            if not li.has_attr("class") or not any(re.match(r"^rare", cls) for cls in li["class"]):
                                rhymes.append(li.text.strip()) if li.text.strip() else None

                    if not rhymes:
                        await message.answer("Рифмы не найдены.")
                        await asyncio.sleep(5)
                        await message.delete()
                        return

                    # Разбиваем рифмы на группы по 20
                    chunks = [rhymes[i:i + 20] for i in range(0, len(rhymes), 20)]

                    # Сохраняем рифмы в состояние
                    await state.update_data(rhymes=chunks, word=word)

                    # Отправляем первую страницу рифм
                    await send_rhymes(message, state, page=0)
                else:
                    logging.warning(f"Ошибка {response.status} при запросе {url}")
                    await message.answer("Ошибка при получении данных с сайта.")
                    await asyncio.sleep(5)
                    await message.delete()
        except Exception as e:
            logging.error(f"Ошибка при парсинге: {e}", exc_info=True)
            await message.answer("Произошла ошибка при обработке запроса.")
            await asyncio.sleep(5)
            await message.delete()


# Функция для отправки рифм с кнопками
async def send_rhymes(message: types.Message, state: FSMContext, page: int):
    data = await state.get_data()
    rhymes = data.get("rhymes", [])
    word = data.get("word", "")
    await state.update_data(
        chat_id=message.chat.id,  # Сохраняем chat_id
        message_id=message.message_id  # Сохраняем message_id
    )
    if not rhymes:
        await message.answer("Рифмы не найдены.")
        await asyncio.sleep(5)
        await message.delete()
        return

    total_pages = len(rhymes)

    # Формируем текст в HTML-формате
    rhymes_text = "<b>Рифмы к слову:</b> <i>{}</i>\n\n{}".format(
        word, "<pre>" + "\n".join(f"• {r}" for r in rhymes[page]) + "</pre>"
    )

    # Сохраняем отправленное сообщение в состояние
    if 'message_sent' not in data:
        message_sent = await message.answer(
            rhymes_text,
            parse_mode="HTML",
            reply_markup=get_pagination_keyboard(page, total_pages)
        )
        # Сохраняем объект сообщения в состояние
        await state.update_data(message_sent=message_sent)
        return

    # Получаем уже отправленное сообщение из состояния
    message_sent = data['message_sent']

    # Для обновления этого сообщения в будущем
    await message_sent.edit_text(
        rhymes_text,
        parse_mode="HTML",
        reply_markup=get_pagination_keyboard(page, total_pages)
    )


# Обработчик кнопок пагинации
@rhyme_router.callback_query(lambda c: c.data.startswith("rhyme_page_"))
async def change_page(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    await send_rhymes(callback.message, state, page)
    await callback.answer()  # Закрываем уведомление
