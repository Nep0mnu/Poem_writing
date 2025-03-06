from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Новый стих"), KeyboardButton(text="Последний стих")],
        [KeyboardButton(text="Все стихи")]
    ],
    resize_keyboard=True,  # Уменьшает размер кнопок
    input_field_placeholder='Пускай накроет вдохновенье...'
)

edit_poetry = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить строчку"),KeyboardButton(text="Рифма к...")],
        [KeyboardButton(text="Сохранить"), KeyboardButton(text="Назад")],
    ],
    resize_keyboard=True,  # Уменьшает размер кнопок
    input_field_placeholder='Пускай накроет вдохновенье...'
)

inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Начать писать", callback_data="start_write")],
        [InlineKeyboardButton(text="Придумай идею", callback_data="idia_help")]
    ]
)

admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пользователи")],
    ],
    resize_keyboard=True,  # Уменьшает размер кнопок
    input_field_placeholder='Босс качалки...'
)