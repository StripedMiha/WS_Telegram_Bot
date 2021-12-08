import datetime
import logging
import asyncio
import re

import aiogram.utils.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Text
from aiogram.utils.callback_data import CallbackData
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from app.config_reader import load_config
from app.auth import TUser
from app.main import see_days_costs, update_day_costs, about_user, menu_buttons, days_costs_for_remove, remove_costs, \
    remove_cost, text_count_removed_costs, bookmarks_for_remove, remove_bookmark_from_user, get_users_of_list, \
    get_project_list, get_tasks, get_list_bookmark, add_costs, INPUT_COST_EXAMPLE, add_bookmark, \
    get_month_stat, select_task, check_task_id, get_text_add_costs

from pprint import pprint

config = load_config("config/bot.ini")
bot = Bot(token=config['tg_bot']['token'], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


class OrderMenu(StatesGroup):
    wait_for_email = State()
    waiting_for_task_id = State()
    waiting_for_time_comment = State()
    wait_for_offer = State()
    wait_news = State()
    wait_for_date = State()


def register_handlers_time_cost(dp: Dispatcher):
    dp.register_message_handler(menu, commands="menu", state="*")
    dp.register_message_handler(wait_offer, state=OrderMenu.wait_for_offer)
    dp.register_message_handler(wait_email, state=OrderMenu.wait_for_email)
    dp.register_message_handler(wait_date, state=OrderMenu.wait_for_date)
    dp.register_message_handler(wait_task_id, state=OrderMenu.waiting_for_task_id)
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
    register_handlers_time_cost(dp)

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()


user_data = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),
        BotCommand(command="/stat", description="Получить месячную статистику")

    ]
    await bot.set_my_commands(commands)  # TODO наверх


def log_in(*arg):
    time = str(datetime.datetime.today())
    string = time + ' ' + ' '.join([str(i) for i in arg])
    with open('users_messages.txt', 'a', encoding='utf-8') as f:
        print(string, file=f)


# Вывод списка комманд
@dp.message_handler(commands="help")
async def cmd_test1(message: types.Message):
    log_in(message.from_user.full_name, message.from_user.id, message.text)
    user = TUser(message.from_user.id, message.from_user.first_name, message.from_user.last_name)
    if not user.has_access:
        if user.blocked:
            return None
        await message.answer('Нет доступа\nНапиши /start в личные сообщения боту, чтобы запросить доступ')
        return None
    text_help = [
        f'<b>Список комманд:</b>',
        f'/menu - меню взаимодействия с WS  через бота',
        f'Перечень действий меню с описанием:',
        f'<b>Обо мне</b> - выводит информацию о вас: Имя, почта и статус',
        f'<b>Найти задачу</b> - открывает подменю выбора способа поиска проекта'
        f' и задачи для внесения часов или добавления задачи в закладки. '
        f'Через поиск по всем доступным вам проектам или через поиск по закладкам, которые вы оставили ранее',
        f'<b>Удалить закладку</b> - удаление закладок',
        f'<b>Отчёт за сегодня</b> - выводит отчёт по вашим введённым за сегодня трудоёмкостям',
        f'<b>Удалить трудоёмкость</b> - удалить одну из сегодняшних трудоёмкостей, введёных по ошибке',
        f'<b>Изменить почту</b> - изменить почту',
        f'<b>Предложение/отзыв о боте</b> - можно предложить фичу, доработку, оставить замечание по работе бота.'
    ]
    answer = '\n'.join(text_help)
    await message.answer(answer)

# Словарь для считывания инлайн кнопок
callback_menu = CallbackData("fab_menu", "action")
callback_auth = CallbackData("fab_auth", "action", "data")
callback_search = CallbackData("fab_search", "action", "path")
callback_remove = CallbackData("fab_remove", "action", 'id')


def get_keyboard_admin(list_data: list[list], width: int = 1, enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons = []
    for text, action, data in list_data:
        buttons.append(types.InlineKeyboardButton(text=text,
                                                  callback_data=callback_auth.new(action=action,
                                                                                  data=data)))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_auth.new(action="cancel",
                                                                                                 data='   ')))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# Формирование инлайн клавиатуры
def get_keyboard(list_data: list[list], width: int = 3, enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons = []
    for name, action in list_data:
        buttons.append(types.InlineKeyboardButton(text=name, callback_data=callback_menu.new(action=action)))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_menu.new(action="cancel")))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


async def get_remove_keyboard(list_data: list[list[str, int, str]],
                              width: int = 1, enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons: list[types.InlineKeyboardButton] = []
    if len(list_data) > 0:
        is_cost_remove = True if (list_data[0][2].split('_')[1] == 'cost' if len(list_data) > 1 else False) else False
        for text, data, action in list_data:
            buttons.append(types.InlineKeyboardButton(text=text,
                                                      callback_data=callback_remove.new(action=action,
                                                                                        id=data)))
        if is_cost_remove:
            buttons.append(types.InlineKeyboardButton(text="Удалить все",
                                                      callback_data=callback_remove.new(action="remove_costs",
                                                                                        id='-')))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена",
                                                  callback_data=callback_remove.new(action="cancel",
                                                                                    id='-')))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# meme_version /start
@dp.message_handler(commands="start")
async def cmd_test1(message: types.Message):
    log_in(message.from_user.id, message.from_user.full_name, message.text)
    if message.chat.type != 'private':
        log_in(message.from_user.full_name, 'Пытается запустить бота в групповом чате')
        return None
    user = TUser(message.from_user.id, message.from_user.first_name, message.from_user.last_name)
    if user.blocked:
        return None
    elif user.get_status() == 'wait':
        await message.answer('Заявка ушла админу. Ждите.')
        data_for_keyboard = [['Добавить пользователя', 'known_user', user.user_id],
                             ['Игнорировать пользователя', 'black_user', user.user_id]]
        keyboard = get_keyboard_admin(data_for_keyboard, width=2, enable_cancel=False)
        await bot.send_message(TUser.get_admin_id(), f"Этот перец пишет мне: {user.full_name}\n"
                                                     f"Пишет вот что: {message.text}", reply_markup=keyboard)
        return None
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{user.first_name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))


@dp.callback_query_handler(callback_auth.filter(action=['known_user', 'black_user']))
async def user_decide(call: types.CallbackQuery, callback_data: dict):
    action = callback_data['action']
    user = TUser(callback_data['data'])
    if action == "known_user":
        user.change_status('user')
        await call.answer(text='Пользователь добавлен', show_alert=True)
        await call.answer()
        await call.message.edit_text(f"Пользователь {user.full_name} добавлен")
        try:
            await bot.send_message(user.user_id, 'Доступ разрешён. \nВведите /start чтобы начать.')
        except aiogram.utils.exceptions.ChatNotFound:
            await bot.send_message(TUser.get_admin_id(),
                                   'Пользователь не получил уведомления, так как не имеет диалога с ботом')
    elif action == "black_user":
        user.change_status('black')
        await call.answer(text='Пользователь добавлен в чёрный список', show_alert=True)
        await call.message.edit_text(f'Пользователь {user.full_name} добавлен в чёрный список')
        try:
            await bot.send_message(user.user_id, 'Вас добавили в чёрный список')
        except aiogram.utils.exceptions.ChatNotFound:
            await bot.send_message(TUser.get_admin_id(),
                                   'Пользователь не получил уведомления, так как не имеет диалога с ботом')


@dp.callback_query_handler(callback_auth.filter(action='cancel'))
async def ad_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text('Выбор отменён.')
    await state.finish()
    await call.answer()


@dp.callback_query_handler(callback_menu.filter(action="cancel"))
async def chose_cancel(call: types.CallbackQuery):
    log_in(call.from_user.full_name, 'cancel')
    await call.message.edit_text("Выбор отменён.")
    await call.answer()


@dp.callback_query_handler(callback_search.filter(action="cancel"))
async def remove_comments(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    await call.message.edit_text("Выбор отменён.")
    return


@dp.message_handler(commands="change_status")
async def status_changer(message: types.Message):
    user = TUser(message.from_user.id)
    if not user.admin:
        return None
    data_for_keyboard = [['Пользователи', 'list_user', ' '],
                         ['Заблокированные', 'list_black', ' ']]
    keyboard = get_keyboard_admin(data_for_keyboard)
    await message.answer('Выбери список для поиска пользователя, которому хочешь изменить статус',
                         reply_markup=keyboard)


@dp.callback_query_handler(callback_auth.filter(action=['list_user', 'list_black']))
async def select_list(call: types.callback_query, callback_data: dict):
    selected_list = callback_data['action'].split('_')[1]
    keyboard = get_keyboard_admin(get_users_of_list(selected_list), width=2)
    await call.message.edit_text('Выберите пользователя:', reply_markup=keyboard)


async def menu(message: types.Message):
    log_in(message.from_user.full_name, message.text)
    user = TUser(message.from_user.id)
    if not user.has_access:
        return None
    buttons = menu_buttons(user)
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))
    await update_day_costs(user)


@dp.callback_query_handler(callback_menu.filter(action=['set email', 'change email', 'about me', 'remove book',
                                                        'daily report', 'offers', 'change date', 'remove time cost']))
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    log_in(call.from_user.full_name, action)
    user = TUser(call.from_user.id)
    date = 'сегодня' if user.get_date() == 'today' else user.get_date()
    if action == 'set email' or action == 'change email':
        await call.message.edit_text('Введите вашу корпоративную почту:\n'
                                     'Введите "Отмена" для отмены ввода')
        await OrderMenu.wait_for_email.set()
    elif action == 'about me':
        await call.message.edit_text(about_user(user))
    elif action == 'daily report':
        await call.message.edit_text(f"<b>Отчёт за {date}:</b>\n\n")
        await call.message.answer(see_days_costs(user))
    elif action == 'offers':
        await call.message.edit_text('Наберите ваше предложение/замечание и отправьте:\n'
                                     'Наберите "Отмена" для отмены.')
        await OrderMenu.wait_for_offer.set()
    elif action == 'remove time cost':
        await call.message.edit_text('Выберите трудоёмкость, которую хотите удалить:',
                                     reply_markup=await get_remove_keyboard(days_costs_for_remove(user)))
    elif action == 'remove book':
        await call.message.edit_text('Выберите закладку, которую хотите удалить:',
                                     reply_markup=await get_remove_keyboard(bookmarks_for_remove(user)))
    elif action == 'change date':
        answer = "Введите дату в формате ДД.ММ.ГГГГ:\n" \
                 "Введите 'сегодня' или 'today', чтобы бот взаимодействовал с днём который будет на тот" \
                 " момент сегодняшним 🤪\n" \
                 "Введите 'вчера' или 'yesterday' для установления вчерашней даты\n"\
                 "Введите 'отмена' для отмены изменения даты"
        await call.message.edit_text(answer)
        await OrderMenu.wait_for_date.set()
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


async def wait_date(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, 'Вводит дату:', message.text)
    user = TUser(message.from_user.id)
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод даты.\n')
        log_in(user.full_name, 'cancel input date')
        await state.finish()
    elif message.text.lower() == 'сегодня' or message.text.lower() == 'today':
        user.change_date('today')
        await message.answer('Теперь бот будет записывать на текущий день')
    elif message.text.lower() == 'вчера' or message.text.lower() == 'yesterday':
        user.change_date('yesterday')
        await message.answer('Установлена вчерашняя дата')
    elif re.match(r'(((0[1-9])|([1-2][0-9])|(3[0-1]))[., :]((0[1-9])|(1[0-2]))[., :]20[2-9][0-9])', message.text):
        date = message.text.strip(' ')
        user.change_date(date)
        await message.answer(f'Установлена дата: {user.get_date()}')
    else:
        await message.answer('Дата введена в неверном формате.')
        return
    await state.finish()
    return


async def wait_email(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    user = TUser(message.from_user.id)
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru|[a-z]\d@s-t.studio', message.text):
        user.change_mail(message.text)
        answer = message.from_user.full_name + ', вы установили почту: ' + user.get_email()
        await message.answer(answer)
    elif message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
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
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        log_in(message.from_user.full_name, 'cancel input offer')
        await message.answer('Отменён ввод.\n')
        await state.finish()
        return
    log_in(message.from_user.full_name, 'offer:', message.text)
    text = message.from_user.full_name + ' воспользовался кнопкой предложений/замечаний.\n' \
                                         '#Отзыв_SMDE_WS_bot\n\n' + message.text
    await bot.send_message(TUser.get_admin_id(), text)
    await message.answer('Улетело админу, спасибо :)')
    await state.finish()


@dp.callback_query_handler(callback_menu.filter(action=['get tasks list']))
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    log_in(call.from_user.full_name, user.get_email(), '- add time cost')
    buttons = [['Через поиск', 'via search'],
               ['❤️ Через закладки', 'via bookmarks'],
               ['Ввести id задачи', 'task id input']]
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


@dp.callback_query_handler(callback_menu.filter(action=['task id input']))
async def task_id_input(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    log_in(user.full_name, call['data'])
    await call.message.edit_text('Введите ID задачи из WorkSection')
    await OrderMenu.waiting_for_task_id.set()


async def wait_task_id(message: types.Message, state: FSMContext):
    user = TUser(message.from_user.id)
    log_in(user.full_name, message.text)
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод ID задачи.\n')
        log_in(user.full_name, 'cancel input task id')
        await state.finish()
    if check_task_id(message.text):
        await state.update_data(id=message.text,
                                user_id=message.from_user.id)
        text = get_tasks(message.text, user.user_id)
        if isinstance(text, list):
            await message.answer('У данной задачи есть подзадачи, пока не могу выбрать эту задачу :С')
            await state.finish()
            return
        await message.answer(text)
        await OrderMenu.waiting_for_time_comment.set()
    else:
        await message.answer('Задачи с этим ID нет у меня :С \nВведите "отмена" для отмены ввода')



@dp.callback_query_handler(callback_menu.filter(action=['via search']))
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    log_in(user.full_name, call['data'])
    user_projects = await get_project_list(user)
    keyboard = await get_remove_keyboard(user_projects, width=2)
    await call.message.edit_text('Выберите проект', reply_markup=keyboard)


@dp.callback_query_handler(callback_menu.filter(action=['via bookmarks']))
async def search_project_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    list_book = get_list_bookmark(call.from_user.id)
    if isinstance(list_book, str):
        await call.message.edit_text(list_book)
        return
    keyboard = await get_remove_keyboard(list_book)
    await call.message.edit_text('Выберите задачу:', reply_markup=keyboard)


@dp.callback_query_handler(callback_remove.filter(action='search_task'))
async def search_tasks_via_search(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    log_in(call.from_user.full_name, call['data'])
    project_id = callback_data['id']
    await call.message.edit_text('Идёт поиск всех задач. Секундочку подождите')
    tasks = get_tasks(project_id, call.from_user.id)
    if isinstance(tasks, str):
        await state.update_data(id=callback_data['id'],
                                user_id=call.from_user.id)
        await call.message.edit_text(tasks)
        await OrderMenu.waiting_for_time_comment.set()
        return None
    keyboard = await get_remove_keyboard(tasks, width=2)
    await call.message.edit_text('Выберите задачу', reply_markup=keyboard)


@dp.callback_query_handler(callback_remove.filter(action=["input_here"]))
async def add_costs_via_bookmarks(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    log_in(call.from_user.full_name, call['data'])
    task_id = callback_data['id']
    text = get_text_add_costs(task_id, TUser(call.from_user.id))
    await state.update_data(id=callback_data['id'],
                            user_id=call.from_user.id)
    await call.message.edit_text(text)
    await OrderMenu.waiting_for_time_comment.set()
    return None


@dp.callback_query_handler(callback_remove.filter(action="remove_bookmark"))
async def remove_user_bookmark(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    remove_bookmark_from_user(callback_data['id'])
    await call.message.edit_text('Закладка удалена')


@dp.callback_query_handler(callback_remove.filter(action=["remove_cost_ws", "remove_costs", "cancel"]))
async def remove_comments(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    action = callback_data['action']
    if action == "cancel":
        await call.message.edit_text("Выбор отменён.")
        return
    elif action == "remove_cost_ws":
        cost_id = callback_data["id"]
        status = remove_cost(cost_id)
        log_in(call.from_user.full_name, status)
        await call.message.edit_text(status)
    elif action == "remove_costs":
        await call.message.edit_text(text_count_removed_costs(call.from_user.id))
        for i_status in remove_costs(TUser(call.from_user.id)):
            await call.message.answer(i_status)
        await call.message.answer('Удаление завершено')
    return


async def wait_hours(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    data = await state.get_data()
    text = message.text
    if 'отмена' in text.lower() or 'cancel' in text.lower():
        await message.answer('Отмена ввода')
        await state.finish()
        return
    elif 'добавить закладку' in text.lower():
        task_id = data['id']
        await message.answer(add_bookmark(message.from_user.id, task_id))
        await state.finish()
    elif 'выбрать' in text.lower() or 'select' in text.lower():
        await message.answer(select_task(message.from_user.id, data['id']))
        await state.finish()
        return
    elif 'ничего не понял' in text.lower() or '!' not in text.lower():
        await message.answer(INPUT_COST_EXAMPLE)
        return
    else:
        for i_status in add_costs(text, data):
            await message.answer(i_status)
        await message.answer('Внесение завершено')
        await state.finish()
        return


@dp.message_handler(commands='news')
async def wait_for_news(message: types.Message):
    log_in(message.from_user.full_name, 'send news')
    if not TUser(message.from_user.id).admin:
        return None
    await message.answer('Введите новость:')
    await OrderMenu.wait_news.set()
    return


# Выбор обеда с клавиатуры
@dp.message_handler(commands="dinner")
async def get_dinner(message: types.Message):
    user = TUser(message.from_user.id)
    if not user.has_access:
        if user.get_status() == 'black' or user.get_status == 'wait':
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "С макарошками"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)

    @dp.message_handler(lambda message_answer: message_answer.text == "С макарошками")
    async def with_pasta(message_answer: types.Message):
        await message_answer.answer_photo(
            'https://otvet.imgsmail.ru/download/214880555_ab5a400b4f358b8003dcdd86d4186d58_800.jpg',
            reply_markup=types.ReplyKeyboardRemove())

    # Обработка ответа выбора обеда
    @dp.message_handler(lambda message_answer: message_answer.text == "С пюрешкой")
    async def with_puree(message_answer: types.Message):
        await message_answer.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())


async def news_to_users(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, 'send news')
    users: list[list[str, int]] = [[i, k] for i, j, k in get_users_of_list('user')]
    for name, user_id in users:
        news = message.text
        text = f'{name}, Это новости бота 🙃\n\n{news}'
        try:
            await bot.send_message(user_id, text)
            await bot.send_message(TUser.get_admin_id(),
                                   f'Новость отправлена пользователю {name} с id {user_id}')
        except aiogram.utils.exceptions.ChatNotFound:
            await bot.send_message(TUser.get_admin_id(),
                                   f'не удалось отправить новость пользователю {name} с id {user_id}')

    await state.finish()
    await message.answer('Отправлено')


@dp.message_handler(commands='log')
async def log_for_admin(message: types.Message):
    log_in(message.from_user.full_name, message.text)
    user = TUser(message.from_user.id)
    if not user.admin:
        return None
    count = int(message.text.split(' ')[1])
    with open('users_messages.txt', 'r', encoding='utf-8') as f:
        text = f.readlines()[-count:]
    answer = ''
    for i in text:
        answer += i
    await bot.send_message(chat_id=message.from_user.id, text=answer)


@dp.message_handler(commands="stat")
async def cmd_stat(message: types.Message):
    log_in(message.from_user.full_name, message.text)
    get_month_stat()
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/1.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')


@dp.message_handler(lambda message_answer: message_answer.text.lower() in ["ввести", "add"])
async def fast_input(message: types.Message, state: FSMContext):
    await message.answer("Да-да?")
    user = TUser(message.from_user.id)
    if user.selected_task is None:
        await message.answer('Задача не выбрана, выбери её через поиск')
        return
    text = get_tasks(user.selected_task, user.user_id)
    await state.update_data(id=user.selected_task,
                            user_id=user.user_id)
    await message.answer(text)
    await OrderMenu.waiting_for_time_comment.set()


# проверка запуска
if __name__ == "__main__":
    asyncio.run(main())
