import logging
import asyncio
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text
from aiogram.utils.callback_data import CallbackData
from aiogram.types import BotCommand, message
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext


from app.config_reader import load_config
from app.handlers.drinks import register_handlers_drinks
from app.handlers.food import available_food_names, available_food_sizes
from app.handlers.drinks import available_bottle_drinks_sizes, available_glasses_drinks_sizes
from app.handlers.drinks import available_bottle_alcohol_drinks_names, available_glasses_alcohol_drinks_names
from app.handlers.drinks import available_bottle_alcohol_free_drinks_names, available_glasses_alcohol_free_drinks_names
# from app.handlers.common import register_handlers_common
from app.auth import *
from ws_api import get_all_project_for_user, get_tasks, search_tasks, get_format_today_costs

from pprint import pprint
from contextlib import suppress
from random import randint

drinks = available_glasses_alcohol_free_drinks_names + available_glasses_alcohol_drinks_names \
         + available_bottle_alcohol_free_drinks_names + available_bottle_alcohol_drinks_names
sizes = available_bottle_drinks_sizes + available_glasses_drinks_sizes

config = load_config("config/bot.ini")
# token = '1909941584:AAHRt33_hZPH9XzGRbQpAyqGzh9sbwEWZtQ'
bot = Bot(token=config.tg_bot.token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


class OrderMenu(StatesGroup):
    wait_for_email = State()
    waiting_for_time_comment = State()
    # waiting_hours = State()
    # waiting_task = State()


def register_handlers_time_cost(dp: Dispatcher):
    dp.register_message_handler(menu, commands="menu", state="*")
    dp.register_message_handler(wait_email, state=OrderMenu.wait_for_email)
    dp.register_message_handler(wait_hours, state=OrderMenu.waiting_for_time_comment)


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
    # register_handlers_common(dp)
    # register_handlers_drinks(dp)
    # register_handlers_food(dp)
    register_handlers_time_cost(dp)

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
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личные сообщения боту, чтобы запросить доступ')
        return None
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

new_user_list = []
callback_ad = CallbackData("fab_num", "action")
# selected_list = ''


def get_keyboard_admin(list_data, width=1):
    buttons = []
    if type(list_data) is list:
        for button in list_data:
            buttons.append(types.InlineKeyboardButton(text=button, callback_data=callback_ad.new(action=button)))
    elif type(list_data) is dict:
        for i, j in list_data.items():
            buttons.append(types.InlineKeyboardButton(text=j, callback_data=callback_ad.new(action=i)))
    buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_ad.new(action="Отмена")))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# meme_version /start
@dp.message_handler(commands="start")
async def cmd_test1(message: types.Message):
    if message.chat.type != 'private':
        print(message.from_user.first_name, message.from_user.last_name, 'дебил')
        return None
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black'):
            return None
        if check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Заявка ушла админу. Ждите.')
        global new_user_list
        new_user_list = [message.from_user.id, message.from_user.first_name, message.from_user.last_name,
                         message.chat.type]
        user_dict = read_json('wait')
        user_dict[message.from_user.id] = ''
        write_json('wait', user_dict)
        await bot.send_message(300617281, f"Этот перец пишет мне: {message.from_user.first_name}\n"
                                          f"Пишет вот что: {message.text}",
                               reply_markup=get_keyboard_admin(['Добавить пользователя', 'Игнорировать пользователя']))
        return None
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{message.from_user.first_name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))


@dp.callback_query_handler(callback_ad.filter(action=['Добавить пользователя', 'Игнорировать пользователя']))
async def user_decide(call: types.CallbackQuery, callback_data: dict):
    print('dorov')
    action = callback_data['action']
    if action == "Добавить пользователя":
        new_user(new_user_list)
        await call.answer(text='Пользователь добавлен', show_alert=True)
        await call.answer()
        await call.message.edit_text('Пользователь {} {} добавлен'.format(new_user_list[1], new_user_list[2]))
        await bot.send_message(new_user_list[0], 'Доступ разрешён.')
        answer = [f"Наталья, морская пехота",
                  f"Стартуем, <i>{new_user_list[1]}!</i>",
                  f"Введи /help чтобы получить список команд"
                  ]
        await bot.send_photo(new_user_list[0], 'https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))
        new_user_list.clear()
    elif action == "Игнорировать пользователя":
        black_user(new_user_list)
        await call.answer(text='Пользователь добавлен в чёрный список', show_alert=True)
        await call.message.edit_text(
            'Пользователь {} {} добавлен в чёрный список'.format(new_user_list[1], new_user_list[2]))
        await bot.send_message(new_user_list[0], 'Вас добавили в чёрный список')


@dp.message_handler(commands="change_status")
async def status_changer(message: types.Message):
    if not check_admin(message.from_user.id):
        return None
    await message.answer('Выбери список для поиска пользователя, которому хочешь изменить статус',
                         reply_markup=get_keyboard_admin(['users', 'black']))


@dp.callback_query_handler(callback_ad.filter(action=['users', 'black']))
async def select_list(call: types.callback_query, callback_data: dict):
    if not check_admin(call['from']['id']):
        await call.message.edit_text('Нет доступа')
        await call.answer()
        return None
    global selected_list
    selected_list = callback_data.get('action')
    await call.message.edit_text('Выберите пользователя:',
                                 reply_markup=get_keyboard_admin(get_list(selected_list), 2))

    @dp.callback_query_handler(callback_ad.filter(action=[i for i in get_list(selected_list).keys()]))
    async def select_user(call: types.callback_query, callback_data: dict):
        if not check_admin(call['from']['id']):
            await call.message.edit_text('Нет доступа')
            await call.answer()
            return None
        id_of = callback_data.get('action')
        users = read_json(selected_list)
        user = users[id_of]
        name = user['first_name'] + ' ' + user['last_name']
        if selected_list == 'users':
            answer = f'Пользователь {name} удалён из списка пользователей.'
        else:
            answer = f'Пользователь {name} удалён из чёрного списка.'
        print(name, 'del from', selected_list)
        change_list(id_of, selected_list)
        await call.message.edit_text(answer)
        await call.answer()


# Выбор обеда с клавиатуры
@dp.message_handler(commands="dinner")
async def get_dinner(message: types.Message):
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "С макарошками"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)

    @dp.message_handler(lambda message: message.text == "С макарошками")
    async def with_pasta(message: types.Message):
        await message.answer_photo(
            'https://otvet.imgsmail.ru/download/214880555_ab5a400b4f358b8003dcdd86d4186d58_800.jpg',
            reply_markup=types.ReplyKeyboardRemove())

    # Обработка ответа выбора обеда
    @dp.message_handler(lambda message: message.text == "С пюрешкой")
    async def with_puree(message: types.Message):
        await message.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())


# Ввод комманды рандомного числа и вывод клавиатура с кнопкой
@dp.message_handler(commands="random")
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
    @dp.callback_query_handler(text="random_value")
    async def send_random_value(call: types.CallbackQuery):
        rnd_num = randint(1, 10)
        await call.message.answer(str(rnd_num))
        # await call.answer(text=f"Случайное число - {rnd_num}.", show_alert=True)
        await call.answer()


# Запуск выбора цифры
@dp.message_handler(commands="numbers")
async def cmd_numbers(message: types.Message):
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
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


# Формирование инлайн клавиатуры отменой
def get_keyboard(list_data, width=3):
    buttons = []
    if type(list_data) is list:
        for button in list_data:
            buttons.append(types.InlineKeyboardButton(text=button, callback_data=callback_fd.new(action=button)))
    elif type(list_data) is dict:
        for i, j in list_data.items():
            buttons.append(types.InlineKeyboardButton(text=j, callback_data=callback_fd.new(action=i)))
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
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    if message.from_user.id not in user_data.keys():
        user_data[message.from_user.id] = fd_dict
    await message.answer("Выберите блюдо:", reply_markup=get_keyboard(available_food_names))

    # Выбор еды
    @dp.callback_query_handler(callback_fd.filter(action=available_food_names))
    async def food_food_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_food"] = callback_data["action"]
        await call.message.edit_text("Выберите размер блюда:", reply_markup=get_keyboard(available_food_sizes))

    # Выбор размеров порции еды
    @dp.callback_query_handler(callback_fd.filter(action=available_food_sizes))
    async def food_size_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_size_food"] = callback_data["action"]
        await call.message.edit_text(f"{call.from_user.first_name}, вы заказали {user_data[call.from_user.id]['Chosen_food']}"
                                     f" порцию {user_data[call.from_user.id]['Chosen_size_food']}.\n"
                                     f"Поробуйте теперь заказать напитки: /drinks")


# Начало выбора напитка
@dp.message_handler(commands="drinks")
async def drinks_start(message: types.Message):
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    if message.from_user.id not in user_data.keys():
        user_data[message.from_user.id] = fd_dict
    await message.answer("Выберите тип напитка:", reply_markup=get_keyboard(["Алкогольный", "Безалкогольный"], 2))

    # Выбор типа напитка
    @dp.callback_query_handler(callback_fd.filter(action=["Алкогольный", "Безалкогольный"]))
    async def drinks_type_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_type_drink"] = callback_data["action"]
        union_data = []
        if callback_data["action"] == "Алкогольный":
            union_data = available_bottle_alcohol_drinks_names + available_glasses_alcohol_drinks_names
        elif callback_data["action"] == "Безалкогольный":
            union_data = available_bottle_alcohol_free_drinks_names + available_glasses_alcohol_free_drinks_names
        await call.message.edit_text(f"Выберите напиток:", reply_markup=get_keyboard(union_data, 3))

    # Выбор напитка
    @dp.callback_query_handler(callback_fd.filter(action=drinks))
    async def drinks_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_drink"] = callback_data["action"]
        union_data = []
        if callback_data["action"] in available_glasses_alcohol_drinks_names \
                or callback_data["action"] in available_glasses_alcohol_free_drinks_names:
            union_data = available_glasses_drinks_sizes
        elif callback_data["action"] in available_bottle_alcohol_drinks_names \
                or callback_data["action"] in available_bottle_alcohol_free_drinks_names:
            union_data = available_bottle_drinks_sizes
        await call.message.edit_text(f"Выберите размер порции:", reply_markup=get_keyboard(union_data, 2))

    # Выбор обьёмов напитка
    @dp.callback_query_handler(callback_fd.filter(action=sizes))
    async def drinks_size_chosen(call: types.CallbackQuery, callback_data: dict):
        user_data[call.from_user.id]["Chosen_size_drink"] = callback_data["action"]
        answer = f"{call.from_user.first_name}, вы заказали {user_data[call.from_user.id]['Chosen_drink']}" \
                 f" в количестве {user_data[call.from_user.id]['Chosen_size_drink']}."
        if user_data[call.from_user.id]['Chosen_type_drink'] == "Алкогольный":
            answer += f"\nБудьте осторожны, алкоголь вредит вашему здоровью!!!"
        if user_data[call.from_user.id]['Chosen_drink'] == 'Энергетик' \
                and user_data[call.from_user.id]['Chosen_size_drink'] != '1 бутылку':
            answer += f"\nБудьте крайне осторожны, есть вероятность увидеть время"
        if str(call.from_user.id) == str(432113264) and user_data[call.from_user.id]['Chosen_drink'] == "Гейская пинаколада":
            answer += f"\nВитя, это тебе!"
        await call.message.edit_text(answer)


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        # BotCommand(command="/drinks", description="Заказать напитки"),
        # BotCommand(command="/food", description="Заказать блюда"),
        # # BotCommand(command="/cancel", description="Отменить текущее действие"),
        # BotCommand(command="/help", description="Показать список команд"),
        # BotCommand(command="/random", description="Рандомное число от 0 до 10"),
        # BotCommand(command="/numbers", description="Выбрать число"),
        BotCommand(command="/menu", description="Взаимодействие с ботом"),


    ]
    await bot.set_my_commands(commands)


# @dp.message_handler(commands="menu")
async def menu(message: types.Message):
    print(message.from_user.full_name, '- menu')
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    # buttons = {
    #     'about me': 'Обо мне',
    #     'add time cost': 'Внести часы',
    #     'add book': 'Добавить закладку',
    #     'daily report': 'Отчёт за сегодня',
    #     'remove time cost': 'Удалить сегодняшнюю трудоёмкость'
    # }
    user_mail = check_mail(message.from_user.id)
    # buttons = {}
    if user_mail is None:
        buttons = {'about me': 'Обо мне',
                   'set email': 'Установить почту'}
    else:
        buttons = {'about me': 'Обо мне',
                   'add time cost': 'Внести часы',
                   'add book': 'Добавить закладку',
                   'daily report': 'Отчёт за сегодня',
                   'remove time cost': 'Удалить трудоёмкость',
                   'change email': 'Изменить почту'}
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))


@dp.callback_query_handler(callback_fd.filter(action=
                                              ['set email', 'change email', 'about me', 'add book', 'daily report',
                                               'remove time cost']))
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    print(call.from_user.full_name, '-', action)
    if action == 'set email' or action == 'change email':
        await call.message.edit_text('Введите почту:')
        await state.update_data(wait_mail=True)
        await OrderMenu.wait_for_email.set()
    elif action == 'about me':
        user_dict = read_json('users').get(str(call.from_user.id))
        status = 'Администратор' if check_admin(str(call.from_user.id)) else 'Пользователь'
        answer = f"Ваше имя - {user_dict['first_name']} {user_dict['last_name']}\n" + \
                 f"Ваша почта - {user_dict.get('email')}\n" + \
                 f"Ваш статус - {status}"
        await call.message.edit_text(answer)
    elif action == 'daily report':
        answer = get_format_today_costs(check_mail(call.from_user.id))
        if answer is None:
            await call.message.edit_text('Вы не внесли трудоёмкости за сегодня.\n'
                                         'Не навлекай на себя гнев Ксении. \n'
                                         'Будь умничкой - внеси часы.')
            return
        await call.message.edit_text('<b>Отчёт за сегодня:</b>\n\n')
        await call.message.answer(answer)
    # elif action == 'remove time cost':
    #     pass #todo удаление трудоёмкости через кнопку
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


# @dp.message_handler(content_types=['text'])
async def wait_email(message: types.Message, state: FSMContext):
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru', message.text):
        edit_mail(message.from_user.id, message.text)
        answer = message.from_user.full_name + ', вы установили почту: ' + check_mail(message.from_user.id)
        await message.answer(answer)
    else:
        await message.answer('Почта введена в неверном формате')
        return
    await state.finish()
    return


@dp.callback_query_handler(callback_fd.filter(action=['add time cost']))
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    print(call.from_user.full_name, '- add time cost')
    buttons = {'via search': 'Через поиск', 'via bookmarks': 'Через закладки'}
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


@dp.callback_query_handler(callback_fd.filter(action=['via search']))
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    user_email = read_json('users').get(str(call.from_user.id)).get('email')
    if user_email is not None:
        user_projects = get_all_project_for_user(user_email)
    user_data[call.from_user.id] = {'path': '/project/'}
    await call.message.edit_text('Выберите проект', reply_markup=get_keyboard(user_projects, 2))


@dp.callback_query_handler(callback_fd.filter(action=['via bookmarks']))
async def search_project_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    await call.message.edit_text('Пока ниработаит :С')
    pass


@dp.callback_query_handler(lambda callback: (callback['data'].split(':')[1]).startswith('id_'))
async def search_tasks_via_search(call: types.CallbackQuery):
    project_id = call['data'].split(':')[1].split('_')[-1]
    user_data[call.from_user.id]['path'] += project_id + '/'
    path = user_data[call.from_user.id].get('path')
    tasks = get_tasks(path)
    await call.message.edit_text('Выберите задачу:', reply_markup=get_keyboard(tasks, 2))


@dp.callback_query_handler(lambda callback: (callback['data'].split(':')[1]).startswith('task_id_'))
async def search_subtasks_via_search(call: types.CallbackQuery):
    task_id = call['data'].split(':')[1].split('_')[-1]
    user_data[call.from_user.id]['path'] += task_id + '/'
    path = user_data[call.from_user.id].get('path')
    tasks = search_tasks(path)
    if tasks.get(task_id) is None or tasks.get(task_id).get('child') is None: # or tasks.get(task_id.get('child') is None):
        await call.message.edit_text("Введите часы и описание деятельности:\n"
                                     "Разделяйте часы и перечень действий символом '!'\n"
                                     "Шаблон: число! деятельность!....! деятельность")
        await OrderMenu.waiting_for_time_comment.set()
        return 0
    subtask = tasks.get(task_id)
    subtasks = subtask.get('child')
    subtasks_buttons = {}
    for i, j in subtasks.items():
        subtasks_buttons['task_id_'+i] = j.get('name')
    await call.message.edit_text('Выберите задачу:', reply_markup=get_keyboard(subtasks_buttons, 2))


@dp.callback_query_handler(lambda callback: True)
async def search_task_via_search(call: types.CallbackQuery):
    pprint(call['data'])
    print('lel')


async def wait_hours(message: types.Message, state: FSMContext):
    text = message.text
    time = text.split('!')[0]
    comment = text.split('!')[1:]
    answer = '<b>Время</b> - ' + time + 'ч\n<b>Проделанная работа</b> - ' + ','.join(comment)
    await message.answer(answer)
    await state.finish()
    pass


# проверка запуска
if __name__ == "__main__":
    asyncio.run(main())
