from aiogram import types, Dispatcher

from random import randint

# from ..Bot import dp
from app.auth import *


# @dp.message_handler(commands="random")
async def cmd_random(message: types.Message):
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Нажми меня', callback_data="random_value"))
    await message.answer("Нажмите на кнопку, чтобы бот отправил число от 1 до 10", reply_markup=keyboard)


# Вывод рандомного числа
# @dp.callback_query_handler(text="random_value")
async def send_random_value(call: types.CallbackQuery):
    rnd_num = randint(1, 10)
    await call.message.answer(str(rnd_num))
    # await call.answer(text=f"Случайное число - {rnd_num}.", show_alert=True)
    await call.answer()


def register_handlers_fun(dp: Dispatcher):
    dp.register_message_handler(cmd_random, commands="random")
    dp.register_callback_query_handler(send_random_value, text="random_value")