from aiogram import types

from app.tgbot.loader import bot, dp
from app.db.structure_of_db import User


# Выбор обеда с клавиатуры
@dp.message_handler(commands="dinner")
async def get_dinner(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if not user.has_access:
        if any(('blocked', 'wait')) in user.get_status():
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "С макарошками", " отмена"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)


# Обработка ответа выбора обеда
@dp.message_handler(lambda message_answer: message_answer.text == "С макарошками")
async def with_pasta(message_answer: types.Message):
    await message_answer.answer_photo(
        'https://otvet.imgsmail.ru/download/214880555_ab5a400b4f358b8003dcdd86d4186d58_800.jpg',
        reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(lambda message_answer: message_answer.text == "С пюрешкой")
async def with_puree(message_answer: types.Message):
    await message_answer.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())
