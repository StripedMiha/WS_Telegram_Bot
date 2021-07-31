import logging
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageNotModified
# from aiogram.dispatcher.filters import Text
from aiogram.utils.callback_data import CallbackData
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.config_reader import load_config
from app.handlers.drinks import register_handlers_drinks
from app.handlers.food import available_food_names, available_food_sizes
from app.handlers.drinks import available_bottle_drinks_sizes, available_glasses_drinks_sizes
from app.handlers.drinks import available_bottle_alcohol_drinks_names, available_glasses_alcohol_drinks_names
from app.handlers.drinks import available_bottle_alcohol_free_drinks_names, available_glasses_alcohol_free_drinks_names
from app.handlers.common import register_handlers_common

from contextlib import suppress
from random import randint

drinks = available_glasses_alcohol_free_drinks_names + available_glasses_alcohol_drinks_names\
         + available_bottle_alcohol_free_drinks_names + available_bottle_alcohol_drinks_names
sizes = available_bottle_drinks_sizes + available_glasses_drinks_sizes


config = load_config("config/bot.ini")
# token = '1909941584:AAHRt33_hZPH9XzGRbQpAyqGzh9sbwEWZtQ'
bot = Bot(token=config.tg_bot.token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


async def main():
    # Настройка логирования в stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.error("Starting bot")

    # парсинг файла конфигурации
    # config = load_config("config/bot.ini")

    # Объявление и инициализация объектов бота и диспетчера
    # bot = Bot(token=config.tg_bot.token)
    # dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация хэндлеров
    register_handlers_common(dp)
    register_handlers_drinks(dp)
    # register_handlers_food(dp)

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()

user_data = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Вывод списка комманд
@dp.message_handler(commands="help")
async def cmd_test1(message: types.Message):
    text_help = [
        f'<b>Список комманд:</b>',
        f'/dinner - получить обед',
        f'/numbers - кнопочки с цыфорками',
        f'/random - рандом цифра',
        f'/food - заказать покушоть',
        f'/drinks - заказать попить',
        f'/cancel или "отмена" - отмена операции'
        ]
    answer = '\n'.join(text_help)
    await message.answer(answer)


# meme_version /start
@dp.message_handler(commands="start")
async def cmd_test1(message: types.Message):
    name = message.from_user['first_name']
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))
    print(message.message_id)


# @dp.message_handler(commands="test4")
# async def with_hidden_link(message: types.Message):
#     await message.answer(
#         f"{fmt.hide_link('https://bezablog.ru/wp-content/uploads/2020/04/%D1%80%D0%B8%D1%81-25.jpg')}"
#         f"Кто бы мог подумать, что "
#         f"в 2020 году в Telegram появятся видеозвонки!\n\nОбычные голосовые вызовы "
#         f"возникли в Telegram лишь в 2017, заметно позже своих конкурентов. А спустя три года, "
#         f"когда огромное количество людей на планете приучились работать из дома из-за эпидемии "
#         f"коронавируса, команда Павла Дурова не растерялась и сделала качественные "
#         f"видеозвонки на WebRTC!\n\nP.S. а ещё ходят слухи про демонстрацию своего экрана :)",
#         parse_mode=types.ParseMode.HTML)


# Выбор обеда с клавиатуры
@dp.message_handler(commands="dinner")
async def get_dinner(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "С макарошками"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)

    @dp.message_handler(lambda message: message.text == "С макарошками")
    async def with_pasta(message: types.Message):
        await message.answer_photo('https://otvet.imgsmail.ru/download/214880555_ab5a400b4f358b8003dcdd86d4186d58_800.jpg',
                                                                               reply_markup=types.ReplyKeyboardRemove())

    # Обработка ответа выбора обеда
    @dp.message_handler(lambda message: message.text == "С пюрешкой")
    async def with_puree(message: types.Message):
        await message.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())


# Ввод комманды рандомного числа и вывод клавиатура с кнопкой
@dp.message_handler(commands="random")
async def cmd_random(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text='Нажми меня', callback_data="random_value"))
    await message.answer("Нажмите на кнопку, чтобы бот отправил число от 1 до 10", reply_markup=keyboard)

    # Вывод рандомного числа
    @dp.callback_query_handler(text="random_value")
    async def send_random_value(call: types.CallbackQuery):
        rnd_num = randint(1, 10)
        await call.message.answer(str(rnd_num))
        # await call.answer(text=f"Случайное число - {rnd_num}.", show_alert=True)
        await call.answer()


# Запуск выбора цифры
@dp.message_handler(commands="numbers")
async def cmd_numbers(message: types.Message):
    # словарь для считывания инлайн кнопок
    callback_numbers = CallbackData("fab_num", "action")

    # Генерация клавиатуры для выбора цирфы
    def get_keyboard_numbers():
        buttons = [
            types.InlineKeyboardButton(text="-1", callback_data=callback_numbers.new(action="decrement")),
            types.InlineKeyboardButton(text="random", callback_data=callback_numbers.new(action="random")),
            types.InlineKeyboardButton(text="+1", callback_data=callback_numbers.new(action="increment")),
            types.InlineKeyboardButton(text="Подтвердить", callback_data=callback_numbers.new(action="finish")),
        ]
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_numbers.new(action="отмена")))
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        keyboard.add(*buttons)
        return keyboard

    # Обновление цифры в клавиатуре при выборе цифры
    async def update_num_text(message: types.Message, new_value: int):
        with suppress(MessageNotModified):
            await message.edit_text(f"Укажите число: {new_value}", reply_markup=get_keyboard_numbers())

    user_data[message.from_user.id] = 0
    await message.answer("Укажите число: 0", reply_markup=get_keyboard_numbers())

    # Выбор цифры
    @dp.callback_query_handler(callback_numbers.filter(action=["increment", "decrement", "random", "отмена"]))
    async def callbacks_num_change(call: types.CallbackQuery, callback_data: dict):
        user_value = user_data.get(call.from_user.id, 0)
        action = callback_data["action"]
        print(action)
        if action == "отмена":
            await call.message.edit_text(f"Выбор числа отменён.")
            await call.answer()
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

    # Вывод выбранной цифры
    @dp.callback_query_handler(callback_numbers.filter(action=["finish"]))
    async def callbacks_num_finish(call: types.CallbackQuery):
        user_value = user_data.get(call.from_user.id, 0)
        await call.message.edit_text(f"Итого: {user_value}")
        await call.answer()


# Словарь для считывания инлайн кнопок
callback_fd = CallbackData("fab_num", "action")


# Формирование инлайн клавиатуры для еды питья с отменой
def get_keyboard_list(list_data: list, width=3):
    buttons = []
    for button in list_data:
        buttons.append(types.InlineKeyboardButton(text=button, callback_data=callback_fd.new(action=button)))
    buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_fd.new(action="Отмена")))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# Инлайн отмена
@dp.callback_query_handler(callback_fd.filter(action="Отмена"))
async def chose_cancel(call: types.CallbackQuery):
    await call.message.edit_text("Выбор отменён.")
    await call.answer()


# Словарь данных пользователя
fd_dict = {"Chosen_food": "",
           "Chosen_size_food": "",
           "Chosen_type_drink": "",
           "Chosen_drink": "",
           "Chosen_size_drink": "",
           }


# Начало /food
@dp.message_handler(commands="food")
async def food_start(message: types.Message):
    if message.from_user.id not in user_data.keys():
        user_data[message.from_user.id] = fd_dict
    await message.answer("Выберите блюдо:", reply_markup=get_keyboard_list(available_food_names))

    # Выбор еды
    @dp.callback_query_handler(callback_fd.filter(action=available_food_names))
    async def food_food_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_food"] = callback_data["action"]
        await call.message.edit_text("Выберите размер блюда:", reply_markup=get_keyboard_list(available_food_sizes))

    # Выбор размеров порции еды
    @dp.callback_query_handler(callback_fd.filter(action=available_food_sizes))
    async def food_size_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_size_food"] = callback_data["action"]
        await call.message.edit_text(f"Вы заказали {user_data[call.from_user.id]['Chosen_food']}"
                                     f" порцию {user_data[call.from_user.id]['Chosen_size_food']}.\n"
                                     f"Поробуйте теперь заказать напитки: /drinks")


# Начало выбора напитка
@dp.message_handler(commands="drinks")
async def drinks_start(message: types.Message):
    if message.from_user.id not in user_data.keys():
        user_data[message.from_user.id] = fd_dict
    await message.answer("Выберите тип напитка:", reply_markup=get_keyboard_list(["Алкогольный", "Безалкогольный"], 2))

    # Выбор типа напитка
    @dp.callback_query_handler(callback_fd.filter(action=["Алкогольный", "Безалкогольный"]))
    async def drinks_type_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_type_drink"] = callback_data["action"]
        if callback_data["action"] == "Алкогольный":
            union_data = available_bottle_alcohol_drinks_names + available_glasses_alcohol_drinks_names
        elif callback_data["action"] == "Безалкогольный":
            union_data = available_bottle_alcohol_free_drinks_names + available_glasses_alcohol_free_drinks_names
        await call.message.edit_text(f"Выберите напиток:", reply_markup=get_keyboard_list(union_data, 3))

    # Выбор напитка
    @dp.callback_query_handler(callback_fd.filter(action=drinks))
    async def drinks_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_drink"] = callback_data["action"]
        if callback_data["action"] in available_glasses_alcohol_drinks_names \
                or callback_data["action"] in available_glasses_alcohol_free_drinks_names:
            union_data = available_glasses_drinks_sizes
        elif callback_data["action"] in available_bottle_alcohol_drinks_names \
                or callback_data["action"] in available_bottle_alcohol_free_drinks_names:
            union_data = available_bottle_drinks_sizes
        await call.message.edit_text(f"Выберите размер порции:", reply_markup=get_keyboard_list(union_data, 2))

    # Выбор обьёмов напитка
    @dp.callback_query_handler(callback_fd.filter(action=sizes))
    async def drinks_size_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_size_drink"] = callback_data["action"]
        answer = f"Вы заказали {user_data[call.from_user.id]['Chosen_drink']}" \
                 f" в количестве {user_data[call.from_user.id]['Chosen_size_drink']}."
        if user_data[call.from_user.id]['Chosen_type_drink'] == "Алкогольный":
            answer += f"\nБудьте осторожны, алкоголь вредит вашему здоровью!!!"
        if user_data[call.from_user.id]['Chosen_drink'] == 'Энергетик'\
                and user_data[call.from_user.id]['Chosen_size_drink'] != '1 бутылку':
            answer += f"\nБудьте крайне осторожны, есть вероятность увидеть время"
        await call.message.edit_text(answer)


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/drinks", description="Заказать напитки"),
        BotCommand(command="/food", description="Заказать блюда"),
        BotCommand(command="/cancel", description="Отменить текущее действие"),
        BotCommand(command="/help", description="Показать список команд"),
        BotCommand(command="/random", description="Рандомное число от 0 до 10"),
        BotCommand(command="/numbers", description="Выбрать число"),

    ]
    await bot.set_my_commands(commands)


# проверка запуска
if __name__ == "__main__":
    asyncio.run(main())
