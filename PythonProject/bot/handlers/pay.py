import logging
import uuid
import base64
import aiohttp
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from config.Ukassa import YOOKASSA_SHOP_ID,YOOKASSA_URL,YOOKASSA_SECRET_KEY
# Настройки YooKassa

storage = MemoryStorage()
pay_router = Router()
logging.basicConfig(level=logging.INFO)

class PaymentState(StatesGroup):
    waiting_for_amount = State()

async def create_payment(amount: float, description: str):
    """Создание платежа в YooKassa"""
    payment_id = str(uuid.uuid4())  # Уникальный ключ
    auth_string = f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_base64}",
        "Idempotence-Key": payment_id  # Теперь здесь
    }

    data = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": "https://web.telegram.org/a/#7549403834"},
        "description": description
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(YOOKASSA_URL, json=data, headers=headers) as response:
            response_data = await response.json()
            if response.status == 200:
                return response_data
            else:
                logging.error(f"Ошибка при создании платежа: {response_data}")
                return None

@pay_router.message(lambda message: message.text.startswith('/pay'))
async def pay_handler(message: Message, state: FSMContext):
    """Обработчик команды /pay"""
    sent_message = await message.answer("Введите сумму добровольного пожертвования в рублях:")
    await state.update_data(chat_id=sent_message.chat.id, message_id=sent_message.message_id)
    await state.set_state(PaymentState.waiting_for_amount)

@pay_router.message(PaymentState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    try:
        await message.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        print(f"Ошибка при удалении сообщения: {e}")
    """Обработчик ввода суммы пользователем"""
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше 0")
    except ValueError:
        await message.answer("Некорректная сумма. Введите число больше 0:")
        return

    await state.clear()
    payment = await create_payment(amount, "Донат")

    if payment and "confirmation" in payment:
        payment_url = payment["confirmation"].get("confirmation_url")
        if payment_url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить", url=payment_url)]])
            await message.answer(f"Сумма: {amount:.2f} ₽\nНажмите кнопку ниже для оплаты:", reply_markup=keyboard)
        else:
            await message.answer("Ошибка: не удалось получить ссылку на оплату.")
    else:
        await message.answer("Ошибка при создании платежа. Попробуйте позже.")
