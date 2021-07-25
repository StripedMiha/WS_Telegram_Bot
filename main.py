import logging
from typing import Text
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.inline_keyboard import InlineKeyboardButton
from aiogram.types.message import Message
from aiogram.utils import callback_data
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text
from aiogram.utils.callback_data import CallbackData


from contextlib import suppress
import aiogram.utils.markdown as fmt
from random import randint

token = '1909941584:AAHRt33_hZPH9XzGRbQpAyqGzh9sbwEWZtQ'
bot = Bot(token=token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot=bot)

user_data = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dp.message_handler(commands="help")
async def cmd_test1(message: types.Message):
    text_help = [
        f'<b>Список комманд:</b>',
        f'/dinner - получить обед',
        f'/numbers - кнопочки с цыфорками',
        f'/random - рандом цифра',
        ]
    answer = '\n'.join(text_help)
    await message.answer(answer)


@dp.message_handler(commands="start")
async def cmd_test1(message: types.Message):
    name = message.from_user['first_name']
    answer = ("Стартуем, " + f"<i>{name}!</i>" +
              f'\nВведи /help чтобы получить список команд'
              )
    await message.answer(answer)
    print(message.message_id)


@dp.message_handler(commands="test4")
async def with_hidden_link(message: types.Message):
    await message.answer(
        f"{fmt.hide_link('https://bezablog.ru/wp-content/uploads/2020/04/%D1%80%D0%B8%D1%81-25.jpg')}"
        f"Кто бы мог подумать, что "
        f"в 2020 году в Telegram появятся видеозвонки!\n\nОбычные голосовые вызовы "
        f"возникли в Telegram лишь в 2017, заметно позже своих конкурентов. А спустя три года, "
        f"когда огромное количество людей на планете приучились работать из дома из-за эпидемии "
        f"коронавируса, команда Павла Дурова не растерялась и сделала качественные "
        f"видеозвонки на WebRTC!\n\nP.S. а ещё ходят слухи про демонстрацию своего экрана :)",
        parse_mode=types.ParseMode.HTML)


@dp.message_handler(commands="dinner")
async def get_dinner(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "Без пюрешки"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == "Без пюрешки")
async def without_puree(message: types.Message):
    await message.answer(f"{message.from_user.first_name}, фу не вкусно", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(lambda message: message.text == "С пюрешкой")
async def with_puree(message: types.Message):
    await message.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands="random")
async def cmd_random(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Нажми меня', callback_data="random_value"))
    await message.answer("Нажмите на кнопку, чтобы бот отправил число от 1 до 10", reply_markup=keyboard)


@dp.callback_query_handler(text="random_value")
async def send_random_value(call: types.CallbackQuery):
    rnd_num = randint(1, 10)
    await call.message.answer(str(rnd_num))
    # await call.answer(text=f"Случайное число - {rnd_num}.", show_alert=True)
    await call.answer()


callback_numbers = CallbackData("fab_num", "action")


def get_keyboard_fab():
    buttons = [
        types.InlineKeyboardButton(text="-1", callback_data=callback_numbers.new(action="decrement")),
        types.InlineKeyboardButton(text="random", callback_data=callback_numbers.new(action="random")),
        types.InlineKeyboardButton(text="+1", callback_data=callback_numbers.new(action="increment")),
        types.InlineKeyboardButton(text="Подтвердить", callback_data=callback_numbers.new(action="finish")),
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(*buttons)
    return keyboard


async def update_num_text(message: types.Message, new_value: int):
    with suppress(MessageNotModified):
        await message.edit_text(f"Укажите число: {new_value}", reply_markup=get_keyboard_fab())


@dp.message_handler(commands="numbers")
async def cmd_numbers(message: types.Message):
    user_data[message.from_user.id] = 0
    await message.answer("Укажите число: 0", reply_markup=get_keyboard_fab())


@dp.callback_query_handler(callback_numbers.filter(action=["increment", "decrement", "random"]))
async def callbacks_num_change(call: types.CallbackQuery, callback_data: dict):
    user_value = user_data.get(call.from_user.id, 0)
    action = callback_data["action"]
    print(action)
    if action == "increment":
        user_data[call.from_user.id] = user_value + 1
        await update_num_text(call.message, user_value + 1)
    elif action == "decrement":
        user_data[call.from_user.id] = user_value - 1
        await update_num_text(call.message, user_value - 1)
    elif action == "random":
        ran_num = randint(-10, 10)
        print(ran_num)
        user_data[call.from_user.id] = ran_num
        await update_num_text(call.message, ran_num)
    await call.answer()


@dp.callback_query_handler(callback_numbers.filter(action=["finish"]))
async def callbacks_num_finish(call: types.CallbackQuery):
    user_value = user_data.get(call.from_user.id, 0)
    await call.message.edit_text(f"Итого: {user_value}")
    await call.answer()


@dp.message_handler(content_types=types.ContentType.TEXT)
async def do_echo(message: types.Message):
    text = message.text
    if text:
        await message.answer(text)


@dp.message_handler(content_types=[types.ContentType.ANIMATION])
async def echo_document(message: types.Message):
    await message.reply_animation(message.animation.file_id)


@dp.message_handler(content_types=[types.ContentType.STICKER])
async def echo_document(message: types.Message):
    await message.answer_sticker(message.sticker.file_id)


def main():
    executor.start_polling(
        dispatcher=dp,
    )


if __name__ == "__main__":
    main()
