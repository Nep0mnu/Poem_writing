import aiohttp
from aiogram import types
from config.YandexGPT import URL, data, headers
import keyboards as kb  # Импорт клавиатуры, если она у тебя есть

async def get_poetry_idea(callback: types.CallbackQuery):
    await callback.answer()  # Закрываем "часики" в Telegram

    async with aiohttp.ClientSession() as session:
        async with session.post(URL, json=data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                idea = result.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "Не удалось получить идею.")
            else:
                idea = "Что вершит судьбы человечества?"

    await callback.message.answer(idea, reply_markup=kb.main)