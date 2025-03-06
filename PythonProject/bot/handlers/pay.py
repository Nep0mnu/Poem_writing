import logging
import uuid
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

YOOKASSA_SHOP_ID = "YOUR_SHOP_ID"
YOOKASSA_SECRET_KEY = "YOUR_SECRET_KEY"
YOOKASSA_URL = "https://api.yookassa.ru/v3/payments"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher()
router = Router()
logging.basicConfig(level=logging.INFO)

class PaymentState(StatesGroup):
    waiting_for_amount = State()

def create_payment(amount: float, description: str):
    payment_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}"
    }
    data = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": "https://t.me/YOUR_BOT_USERNAME"},
        "description": description,
        "idempotency_key": payment_id
    }
    response = requests.post(YOOKASSA_URL, json=data, headers=headers)
    return response.json()

@router.message(lambda message: message.text.startswith('/pay'))
async def pay_handler(message: Message, state: FSMContext):
    await message.answer("Введите сумму платежа в рублях:")
    await state.set_state(PaymentState.waiting_for_amount)

@router.message(PaymentState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше 0")
    except ValueError:
        await message.answer("Некорректная сумма. Введите число больше 0:")
        return

    await state.clear()
    payment = create_payment(amount, "Донат")

    if "confirmation" in payment:
        payment_url = payment["confirmation"]["confirmation_url"]
        keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Оплатить", url=payment_url))
        await message.answer(f"Сумма: {amount:.2f} ₽\nНажмите кнопку ниже для оплаты:", reply_markup=keyboard)
    else:
        await message.answer("Ошибка при создании платежа.")

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
