from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
import keyboards as kb
from bot.database import AsyncSessionLocal, User
from sqlalchemy.future import select

class Reg(StatesGroup):
    name = State()

router_start = Router()

@router_start.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    async with AsyncSessionLocal() as session:
        # Проверяем, есть ли пользователь в базе
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar()

        if not user:
            # Если нет, добавляем нового пользователя
            new_user = User(id=user_id, username=username, first_name=first_name, last_name=last_name)
            session.add(new_user)
            await session.commit()

    await message.answer(
        "Привет! 👋 Добро пожаловать в бота для создания стихов!",
        reply_markup=kb.main  # Отправляем клавиатуру
    )