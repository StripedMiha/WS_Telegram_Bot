import datetime
import logging
import asyncio
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher.filters import Text, IDFilter
from aiogram.utils.callback_data import CallbackData
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from app.config_reader import load_config
from app.handlers.food import available_food_names, available_food_sizes
from app.handlers.drinks import available_bottle_drinks_sizes, available_glasses_drinks_sizes
from app.handlers.drinks import available_bottle_alcohol_drinks_names, available_glasses_alcohol_drinks_names
from app.handlers.drinks import available_bottle_alcohol_free_drinks_names, available_glasses_alcohol_free_drinks_names
from app.auth import *
from ws_api import get_all_project_for_user, get_tasks, search_tasks, get_format_today_costs, remove_cost, add_cost,\
    get_task_info
from app.fun import register_handlers_fun

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
    wait_for_offer = State()
    wait_news = State()


def register_handlers_time_cost(dp: Dispatcher):
    dp.register_message_handler(menu, commands="menu", state="*")
    dp.register_message_handler(wait_offer, state=OrderMenu.wait_for_offer)
    dp.register_message_handler(wait_email, state=OrderMenu.wait_for_email)
    dp.register_message_handler(wait_hours, state=OrderMenu.waiting_for_time_comment)
    dp.register_message_handler(news_to_users, state=OrderMenu.wait_news)


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
    register_handlers_fun(dp)
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


def log_in(*arg):
    time = str(datetime.datetime.today())
    string = time + ' ' + ' '.join([str(i) for i in arg])
    with open('users_messages.txt', 'a', encoding='utf-8') as f:
        print(string, file=f)


# Вывод списка комманд
@dp.message_handler(commands="help")
async def cmd_test1(message: types.Message):
    log_in(message.from_user.full_name, message.from_user.id, message.text)
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личные сообщения боту, чтобы запросить доступ')
        return None
    text_help = [
        f'<b>Список комманд:</b>',
        f'/menu - меню взаимодействия с WS  через бота',
        f'Перечень действий меню с описанием:',
        f'<b>Обо мне</b> - выводит информацию о вас: Имя, почта и статус',
        f'<b>Найти задачу</b> - открывает подменю выбора способа поиска проекта и задачи для внесения часов или добавления задачи в закладки. '
        f'Через поиск по всем доступным вам проектам или через поиск по закладкам, которые вы оставили ранее',
        f'<b>Удалить закладку</b> - удаление закладок',
        f'<b>Отчёт за сегодня</b> - выводит отчёт по вашим введённым за сегодня трудоёмкостям',
        f'<b>Удалить трудоёмкость</b> - удалить одну из сегодняшних трудоёмкостей, введёных по ошибке',
        f'<b>Изменить почту</b> - изменить почту',
        f'<b>Предложение/отзыв о боте</b> - можно предложить фичу, доработку, оставить замечание по работе бота.'
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
        log_in(message.from_user.full_name, 'не прав')
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
        await bot.send_photo(new_user_list[0], 'https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg',
                             caption='\n'.join(answer))
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
        log_in(name, 'del from', selected_list)
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


# # Ввод комманды рандомного числа и вывод клавиатура с кнопкой
# @dp.message_handler(commands="random")
# async def cmd_random(message: types.Message):
#     if not check_user(message.from_user.id):
#         if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
#             return None
#         await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
#         return None
#     keyboard = types.InlineKeyboardMarkup()
#     keyboard.add(types.InlineKeyboardButton(text='Нажми меня', callback_data="random_value"))
#     await message.answer("Нажмите на кнопку, чтобы бот отправил число от 1 до 10", reply_markup=keyboard)
#
#     # Вывод рандомного числа
#     @dp.callback_query_handler(text="random_value")
#     async def send_random_value(call: types.CallbackQuery):
#         rnd_num = randint(1, 10)
#         await call.message.answer(str(rnd_num))
#         # await call.answer(text=f"Случайное число - {rnd_num}.", show_alert=True)
#         await call.answer()


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
# callback_task = CallbackData("fab_task", "action", "page", "id")


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
    log_in(call.from_user.full_name, 'cancel')
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
        await call.message.edit_text(f"{call.from_user.first_name}, вы заказали"
                                     f" {user_data[call.from_user.id]['Chosen_food']}"
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
        if str(call.from_user.id) == str(432113264) and \
                user_data[call.from_user.id]['Chosen_drink'] == "Гейская пинаколада":
            answer += f"\nВитя, это тебе!"
        await call.message.edit_text(answer)


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),

    ]
    await bot.set_my_commands(commands)


async def menu(message: types.Message):
    log_in(message.from_user.full_name, message.text)
    log_in(message.from_user.full_name, 'menu')
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black') and check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    user_mail = check_mail(message.from_user.id)
    if user_mail is None:
        buttons = {'about me': 'Обо мне',
                   'set email': 'Установить почту'}
    else:
        buttons = {'daily report': 'Отчёт за сегодня',
                   'search task': 'Найти задачу',
                   'remove time cost': 'Удалить трудоёмкость',
                   'remove book': 'Удалить закладку',
                   'about me': 'Обо мне',
                   'change email': 'Изменить почту',
                   'offers': 'Предложение/отзыв о боте'}
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))


callback_remove = CallbackData("fab_task", "page", "id", "action")


@dp.callback_query_handler(callback_fd.filter(action=['set email', 'change email', 'about me', 'remove book',
                                                      'daily report', 'remove time cost', 'offers']))
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    log_in(call.from_user.full_name, action)
    if action == 'set email' or action == 'change email':
        await call.message.edit_text('Введите вашу корпоративную почту:\n'
                                     'Введите "Отмена" для отмены ввода')
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
    elif action == 'remove time cost':
        comment = get_format_today_costs(check_mail(str(call.from_user.id)), True)
        buttons = []
        for i in comment:
            buttons.append(types.InlineKeyboardButton(text=(i.get('time_cost') + i.get('comment') +
                                                            ' ' + i.get('task_name')),
                                                      callback_data=callback_remove.new(id=i.get('comment_id'),
                                                                                        page=i.get('page'),
                                                                                        action="remove_one")))
        buttons.append(types.InlineKeyboardButton(text='Отмена',
                                                  callback_data=callback_remove.new(page="---",
                                                                                    id="---",
                                                                                    action="cancel")))
        buttons.append(types.InlineKeyboardButton(text='Удалить все',
                                                  callback_data=callback_remove.new(page="---",
                                                                                    id="---",
                                                                                    action="remove_all")))
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text('Выберите трудоёмкость, которую хотите удалить:', reply_markup=keyboard)
    elif action == 'offers':
        await call.message.edit_text('Наберите ваше предложение/замечание и отправьте:\n'
                                     'Наберите "Отмена" для отмены.')
        await OrderMenu.wait_for_offer.set()
    elif action == 'remove book':
        user_book = read_json('users').get(str(call.from_user.id)).get('bookmarks')
        buttons = []
        for i in user_book:
            buttons.append(types.InlineKeyboardButton(text=i.get('project_name') + ' // ' + i.get('task_name'),
                                                      callback_data=callback_remove.new(id='---',
                                                                                        page=i.get('path'),
                                                                                        action="remove_bookmark")))
        buttons.append(types.InlineKeyboardButton(text='Отмена',
                                                  callback_data=callback_remove.new(page="---",
                                                                                    id="---",
                                                                                    action="cancel")))
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text('Выберите закладку, которую хотите удалить:', reply_markup=keyboard)
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


async def wait_email(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru', message.text):
        edit_mail(message.from_user.id, message.text)
        answer = message.from_user.full_name + ', вы установили почту: ' + check_mail(message.from_user.id)
        await message.answer(answer)
    elif message.text.lower() == 'отмена':
        await message.answer('Отменён ввод почты.\n')
        log_in(message.from_user.full_name, 'cancel input email')
        await state.finish()
    else:
        await message.answer('Почта введена в неверном формате.\n'
                             'Введите "Отмена" для отмены ввода')
        return
    await state.finish()
    return


async def wait_offer(message: types.Message, state: FSMContext):
    if message.text.lower() == 'отмена':
        log_in(message.from_user.full_name, 'cancel input offer')
        await message.answer('Отменён ввод.\n')
        await state.finish()
        return
    log_in(message.from_user.full_name, 'offer:', message.text)
    text = message.from_user.full_name + ' воспользовался кнопкой предложений/замечаний.\n' \
                                         '#Отзыв_SMDE_WS_bot\n\n' + message.text
    await bot.send_message(300617281, text)
    await message.answer('Улетело админу, спасибо :)')
    await state.finish()


@dp.callback_query_handler(callback_fd.filter(action=['search task']))
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, check_mail(str(call.from_user.id)), '- add time cost')
    buttons = {'via search': 'Через поиск', 'via bookmarks': 'Через закладки'}
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


@dp.callback_query_handler(callback_fd.filter(action=['via search']))
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    user_email = read_json('users').get(str(call.from_user.id)).get('email')
    if user_email is not None:
        user_projects = get_all_project_for_user(user_email)
    user_data[call.from_user.id] = {'path': '/project/'}
    await call.message.edit_text('Выберите проект', reply_markup=get_keyboard(user_projects, 2))


@dp.callback_query_handler(callback_fd.filter(action=['via bookmarks']))
async def search_project_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    list_book = get_list_bookmarks(call.from_user.id)
    if list_book is None:
        await call.message.edit_text('У вас нет закладок.\n Добавить закладки можно через кнопку "Найти задачу"')
        return
    else:
        buttons = []
        for i in list_book:
            prj_name = i.get('project_name')
            if len(prj_name.split(' ')) > 2:
                prj_name = ' '.join(prj_name.split(' ')[:2])
            buttons.append(types.InlineKeyboardButton(text=prj_name + ' // ' + i.get('task_name'),
                                                      callback_data=callback_remove.new(page=i.get('path'),
                                                                                        id="---",
                                                                                        action="add_costs")))
        buttons.append(types.InlineKeyboardButton(text='Отмена',
                                                  callback_data=callback_remove.new(page="---",
                                                                                    id="---",
                                                                                    action="cancel")))
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text('Выберите задачу:', reply_markup=keyboard)
    return


@dp.callback_query_handler(lambda callback: callback['data'].split(':')[1].startswith('id_'))
async def search_tasks_via_search(call: types.CallbackQuery):
    log_in(call.from_user.full_name, call['data'])
    project_id = call['data'].split(':')[1].split('_')[-1]
    user_data[call.from_user.id]['path'] += project_id + '/'
    path = user_data[call.from_user.id].get('path')
    tasks = get_tasks(path)
    await call.message.edit_text('Выберите задачу:', reply_markup=get_keyboard(tasks, 2))


INPUT_COSTS = """
Введите часы и описание деятельности:
Можно ввести в одну строку, можно в несколько(но в одном сообщении).
В начале указываете количество часов, следом через '!' можно перечислить один или несколько комментариев.
Можно ввести больше двух часов. Алгоритм сам разделит по два часа. Пробелы между '!' не важны

Для отмены введите '<i>отмена</i>'
Для более подробного описания введите '<i>Ничего не понял</i>'
Для добавления задачи в закладки введите '<i>Добавить закладку</i>'
"""
# "Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> !"
# " <i>Сборка печатного прототипа</i>"
# "\n\n"
# "Пример№2:\n<i>0.5</i>! <i>Печать деталей корпуса</i> \n"
# "<i>2.5</i>! <i>Сборка печатного прототипа</i>\n\n"
# "В первом примере в бот разделит указанное количество часов на количество задач,"
# "в данном случае в WS улетит две записи по полтора часа.\n"
# "Во втором примере в WS улетит 3 записи:\n"
# "Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся "
# "на две записи: на запись с двумя часами и запись с получасом."
# """


@dp.callback_query_handler(lambda callback: (callback['data'].split(':')[1]).startswith('task_id_'))
async def search_subtasks_via_search(call: types.CallbackQuery):
    log_in(call.from_user.full_name, call['data'])
    task_id = call['data'].split(':')[1].split('_')[-1]
    user_data[call.from_user.id]['path'] += task_id + '/'
    path = user_data[call.from_user.id].get('path')
    tasks = search_tasks(path)
    if tasks.get(task_id) is None or tasks.get(task_id).get('child') is None:
        await call.message.edit_text(INPUT_COSTS)
        await OrderMenu.waiting_for_time_comment.set()
        return 0
    subtask = tasks.get(task_id)
    subtasks = subtask.get('child')
    subtasks_buttons = {}
    for i, j in subtasks.items():
        subtasks_buttons['task_id_' + i] = j.get('name')
    await call.message.edit_text('Выберите задачу:', reply_markup=get_keyboard(subtasks_buttons, 2))


@dp.callback_query_handler(callback_remove.filter(action=["add_costs"]))
async def add_costs_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    user_data[call.from_user.id] = {'path': callback_data['page']}
    await call.message.edit_text(INPUT_COSTS)
    await OrderMenu.waiting_for_time_comment.set()
    return


@dp.callback_query_handler(callback_remove.filter(action="remove_bookmark"))
async def remove_user_bookmark(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    page = callback_data['page']
    remove_bookmark(call.from_user.id, page)
    await call.message.edit_text('Закладка удалена')


@dp.callback_query_handler(callback_remove.filter(action=["remove_one", "remove_all", "cancel"]))
async def remove_comments(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    action = callback_data['action']
    if action == "cancel":
        await call.message.edit_text("Выбор отменён")
        return
    elif action == "remove_all":
        comments = get_format_today_costs(check_mail(str(call.from_user.id)), True)
        await call.message.edit_text('Будет удалено ' + str(len(comments)) + ' записей')
        for comment in comments:
            page = comment.get('page')
            comment_id = comment.get('comment_id')
            status = remove_cost(page, comment_id)
            answer = 'Успешно удалено' if status == 'ok' else 'Не успех'
            log_in(call.from_user.full_name, answer)
            await call.message.answer(answer)
    elif action == "remove_one":
        page, comment_id = callback_data["page"], callback_data["id"]
        status = remove_cost(page, comment_id)
        answer = 'Успешно удалено' if status == 'ok' else 'Не успех'
        log_in(call.from_user.full_name, answer)
        await call.message.edit_text(answer)
    return


async def add_costs(text, id_user):
    path = user_data[id_user]['path']
    email = check_mail(str(id_user))
    full_name = check_mail(id_user, 'first_name') + ' ' + check_mail(id_user, 'last_name')
    for string in text.split('\n'):
        time_str = string.split('!')[0]
        time = float(time_str.replace(',', '.') if ',' in time_str else time_str)
        comment = [i.strip(' ') for i in string.split('!')[1:]]  # Удаление пробелов в начале и концекаждой задачи
        if '' in comment:
            comment.remove('')
        for i in comment:
            comment_time = time/len(comment)
            if comment_time > 2:
                q_time = comment_time
                while q_time > 2:
                    q_time -= 2
                    status = add_cost(path, email, i, 2)
                    if status == 'ok':
                        log_in(full_name, 'add comments', path, email, i, 2)
                        answer = 'Успешно внесено'
                    else:
                        answer = 'Не успех'
                    await bot.send_message(int(id_user), answer)
                status = add_cost(path, email, i, q_time)
                if status == 'ok':
                    log_in(full_name, 'add comments', path, email, i, q_time)
                    answer = 'Успешно внесено'
                else:
                    answer = 'Не успех'
                await bot.send_message(int(id_user), answer)
            else:
                status = add_cost(path, email, i, comment_time)
                if status == 'ok':
                    log_in(full_name, 'add comments', path, email, i, comment_time)
                    answer = 'Успешно внесено'
                else:
                    answer = 'Не успех'
                await bot.send_message(int(id_user), answer)


async def wait_hours(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    text = message.text
    if 'отмена' in text.lower():
        await message.answer('Отмена ввода')
        await state.finish()
        return
    if 'добавить закладку' in text.lower():
        path = user_data[message.from_user.id]['path']
        info = get_task_info(path)
        if info.get('status') == 'ok':
            info = info.get('data')
            data = {
                'project_name': info.get('project').get('name'),
                'task_name': info.get('name'),
                'path': path
            }
            status = add_bookmark(message.from_user.id, data)
            if status:
                log_in(message.from_user.id, 'bookmark added')
                await bot.send_message(message.from_user.id, "Закладка добавлена")
            else:
                log_in(message.from_user.id, 'bookmark not added')
                await bot.send_message(message.from_user.id, "Такая закладка уже есть. Отмена")
        else:
            await message.answer('Ошибка бота/сервера\n'
                                 'Оставьте отзыв боту о возникшей ошибке\n'
                                 ':с')
        await state.finish()
        return
    if 'ничего не понял' in text.lower() or '!' not in text:
        await message.answer("Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> !"
                             " <i>Сборка печатного прототипа</i>"
                             "\n\n"
                             "Пример№2:\n<i>0.5</i>! <i>Печать деталей корпуса</i> \n"
                             "<i>2.5</i>! <i>Сборка печатного прототипа</i>\n\n"
                             "В первом примере в бот разделит указанное количество часов на количество задач,"
                             "в данном случае в WS улетит две записи по полтора часа.\n"
                             "Во втором примере в WS улетит 3 записи:\n"
                             "Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся "
                             "на две записи: на запись с двумя часами и запись с получасом.")
        return
    await add_costs(text, message.from_user.id)
    # answer2 = '<b>Время</b> - ' + str(time) + 'ч\n<b>Проделанная работа</b> - ' + ', '.join(comment)
    # await message.answer(answer2)
    await state.finish()


@dp.message_handler(commands='news')
async def wait_for_news(message: types.Message):
    log_in(message.from_user.id, '')
    if check_admin(message.from_user.id) is None:
        return None
    await message.answer('Введите новость:')
    await OrderMenu.wait_news.set()
    return


async def news_to_users(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, 'send news')
    if not check_admin(message.from_user.id):
        return None
    users = read_json('users')
    for i in users.keys():
        name = users.get(i).get('first_name') + ' ' + users.get(i).get('last_name')
        news = message.text
        text = f'{name}, Это новости бота 🙃\n\n{news}'
        await bot.send_message(int(i), text)
    await state.finish()
    await message.answer('Отправлено')


@dp.message_handler(commands='log')
async def log_for_admin(message: types.Message):
    log_in(message.from_user.full_name, message.text)
    if not check_admin(message.from_user.id):
        return None
    count = int(message.text.split(' ')[1])
    text = ''
    with open('users_messages.txt', 'r', encoding='utf-8') as f:
        text = f.readlines()[-count:]
    answer = ''
    for i in text:
        answer += i
    await bot.send_message(chat_id=message.from_user.id, text=answer)


# проверка запуска
if __name__ == "__main__":
    asyncio.run(main())
