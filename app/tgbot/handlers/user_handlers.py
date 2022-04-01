import datetime
import logging
import re
from typing import Union

import sqlalchemy.exc
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData

from app.KeyboardDataClass import KeyboardData
from app.tgbot.loader import dp, bot
from app.create_log import setup_logger
from app.db.structure_of_db import User, Bookmark, Task
from app.exceptions import FutureDate, CancelInput, WrongDate
from app.tgbot.handlers.admin_handlers import get_keyboard_admin
from app.back.main import see_days_costs, get_about_user_info, menu_buttons, days_costs_for_remove, remove_costs, \
    remove_cost, text_count_removed_costs, bookmarks_for_remove, get_project_list, get_tasks, get_list_bookmark, \
    add_costs, INPUT_COST_EXAMPLE, add_bookmark, get_text_add_costs, remind_settings_button, \
    get_text_menu_notification, fast_date_keyboard, change_date, get_subtasks, check_user, create_task

user_logger: logging.Logger = setup_logger("App.Bot.user", "app/log/user.log")


class OrderMenu(StatesGroup):
    wait_for_email = State()
    wait_for_email_for_login = State()
    waiting_for_task_id = State()
    waiting_for_time_comment = State()
    wait_for_offer = State()
    wait_for_date = State()
    wait_for_notification_time = State()
    wait_for_task_name = State()


# Набор кнопок выбора даты
DATE_BUTTONS = ["Вчера", "Сегодня", "Отмена"]

# Набор кнопок выбора действия с задачей
TASK_BUTTONS = ["Выбрать по умолчанию", "Добавить закладку", "Ничего не понял", "Отмена"]

CANCEL_BUTTON = ["Отмена"]


# Создание клавиатуры быстрого набора
def get_fast_keyboard(buttons: list) -> types.ReplyKeyboardMarkup:
    fast_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    fast_keyboard.add(*buttons)
    return fast_keyboard


# Словарь для считывания инлайн кнопок
callback_menu = CallbackData("fab_menu", "action")
callback_search = CallbackData("fab_search", "action", "path")
callback_remove = CallbackData("fab_remove", "action", 'id')


# Формирование инлайн клавиатуры меню
def get_keyboard(list_data: list[list], width: int = 3, enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons = []
    for name, action in list_data:
        buttons.append(types.InlineKeyboardButton(text=name, callback_data=callback_menu.new(action=action)))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_menu.new(action="cancel")))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# Формирование инлайн клавиатуры для поиска, задач\трудоёмкостей\закладок
async def get_remove_keyboard(list_data: list[KeyboardData],
                              width: int = 1, enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons: list[types.InlineKeyboardButton] = []
    if len(list_data) > 0:
        is_cost_remove = True if (list_data[0].action.split('_')[1] == 'cost' and len(list_data) > 1) else False
        for i in list_data:
            buttons.append(types.InlineKeyboardButton(text=i.text,
                                                      callback_data=callback_remove.new(action=i.action,
                                                                                        id=i.id)))
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


# Вывод списка команд
@dp.message_handler(commands="help")
async def request_help(message: types.Message):
    user_logger.info("%s %s %s" % (message.from_user.full_name, message.from_user.id, message.text))
    user: User = User.get_user_by_telegram_id(message.from_user.id, message.from_user.first_name,
                                              message.from_user.last_name)
    if not user.has_access:
        if user.is_blocked:
            return None
        await message.answer('Нет доступа\nНапиши /start в личные сообщения боту, чтобы запросить доступ')
        return None
    text_help = [
        f'/help - Список команд',
        f'/help_manager - помощь по командам менеджеров',
        f'/help_top - помощь по командам управления',
        f'<b>Список команд:</b>',
        f'/menu - меню взаимодействия с WS  через бота',
        f'Перечень действий меню с описанием:',
        f'<b>Обо мне</b> - выводит информацию о вас: Имя, почта и статус',
        f'<b>Найти задачу</b> - открывает подменю выбора способа поиска проекта'
        f' и задачи для внесения часов или добавления задачи в закладки. '
        f'Через поиск по всем доступным вам проектам или через поиск по закладкам, которые вы оставили ранее',
        f'<b>Удалить закладку</b> - удаление закладок',
        f'<b>Отчёт за сегодня</b> - выводит отчёт по вашим введённым за сегодня трудоёмкостям',
        f'<b>Удалить трудоёмкость</b> - удалить одну из сегодняшних трудоёмкостей, введённых по ошибке',
        f'<b>Изменить почту</b> - изменить почту',
        f'<b>Предложение/отзыв о боте</b> - можно предложить фичу, доработку, оставить замечание по работе бота.'
    ]
    answer = '\n'.join(text_help)
    await message.answer(answer)


# Мем версия /start
@dp.message_handler(commands="start")
async def lets_start(message: types.Message):
    user_logger.info("Пользователь %s с id%s ввёл команду /start" % (message.from_user.full_name, message.from_user.id))
    if message.chat.type != 'private':
        user_logger.info("Пользователь %s с id%s пытается запустить бота в групповом чате"
                         % (message.from_user.full_name, message.from_user.id))
        return None
    user = await check_user(message.from_user.id)
    if isinstance(user, list):
        keyboard = get_keyboard(user, width=1, enable_cancel=False)
        await message.answer("Вы бывали ранее в Worksection'e?", reply_markup=keyboard)
        return
    if not user.has_access():
        return None
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{user.first_name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))


#
@dp.callback_query_handler(callback_menu.filter(action="new_user"))
async def user_is_new_user(call: types.CallbackQuery):
    user: User = User.new_user(call.from_user.id, call.from_user.first_name, call.from_user.last_name)
    if "wait" in user.get_status():
        data_for_keyboard = [KeyboardData('Добавить пользователя', user.user_id, 'add_user'),
                             KeyboardData('Игнорировать пользователя', user.user_id, 'block_user')]
        keyboard = get_keyboard_admin(data_for_keyboard, width=1, enable_cancel=False)
        await bot.send_message(User.get_admin_id(), f"Этот перец пишет мне: {user.full_name()}\n",
                               reply_markup=keyboard)
        await call.message.edit_text('Заявка ушла админу. Ждите.')
    return None


#
@dp.callback_query_handler(callback_menu.filter(action="old_user"))
async def user_is_old_user(call: types.CallbackQuery):
    await call.message.edit_text("Введите свою корпоративную почту")
    await OrderMenu.wait_for_email_for_login.set()


@dp.message_handler(state=OrderMenu.wait_for_email_for_login)
async def wait_email_for_login(message: types.Message, state: FSMContext):
    user_logger.info("%s Вводит почту: %s" % (message.from_user.full_name, message.text))
    email = message.text.strip(" ")
    # if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru|[a-z]\d@s-t.studio', email):
    if email in User.get_empty_email():
        un_auth_user = User.new_user(message.from_user.id, message.from_user.first_name, message.from_user.last_name)
        data = "_".join([str(un_auth_user.telegram_id), email])
        data_for_keyboard = [KeyboardData('Добавить пользователя', data, 'auth_user'),
                             KeyboardData('Игнорировать пользователя', data, 'unauth_user')]
        keyboard = get_keyboard_admin(data_for_keyboard, width=1, enable_cancel=False)
        exist_user: User = User.get_user_by_email(email)
        await bot.send_message(User.get_admin_id(), f"Этот перец пишет мне: {un_auth_user.full_name()} "
                                                    f"c id{un_auth_user.telegram_id} {message.from_user.username}\n"
                                                    f"И утверждает, что он {exist_user.full_name()} и почта: {email} его"
                               , reply_markup=keyboard)
        await message.answer('Заявка ушла админу. Ждите.')
        await state.finish()
        return None

    elif message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод почты.\n')
        user_logger.info("%s Отменяет ввод почты" % message.from_user.full_name)
        # await state.finish()
    else:
        await message.answer('Почта введена в неверном формате.\n'
                             'Введите "Отмена" для отмены ввода')
        return
    await state.finish()
    return


# Нажали кнопку отмены
@dp.callback_query_handler(callback_menu.filter(action="cancel"))
@dp.callback_query_handler(callback_search.filter(action="cancel"))
@dp.callback_query_handler(callback_remove.filter(action="cancel"))
async def choice_cancel(call: types.CallbackQuery):
    user_logger.info("Пользователь %s выбрал отмену" % call.from_user.full_name)
    await call.message.edit_text("Выбор отменён.")
    await call.answer()


# Ввели команду /menu
@dp.message_handler(commands="menu", state="*")
async def menu(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("Пользователь %s ввёл команду /menu" % user.full_name())
    if not user.has_access():
        return None
    buttons = menu_buttons(user)
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))


# Нажали кнопку в меню
@dp.callback_query_handler(callback_menu.filter(action=['set email', 'change email', 'about me', 'remove book',
                                                        'daily report', 'offers', 'change date', 'remove time cost']))
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    user_logger.info("%s выбрал кнопку %s" % (user.full_name(), action))
    date = user.get_date(True)
    if action == 'set email':  # or action == 'change email':
        await call.message.edit_text('Введите вашу корпоративную почту:\n'
                                     'Введите "Отмена" для отмены ввода')
        await OrderMenu.wait_for_email.set()
    elif action == 'about me':
        await call.message.edit_text(get_about_user_info(user))
    elif action == 'daily report':
        await call.message.edit_text(f"<b>Отчёт за {date}:</b>\n\n")
        await call.message.answer(await see_days_costs(user))
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
        answer = "Установленная дата: %s\n" \
                 "Введите дату в формате ДД.ММ.ГГГГ:\n" \
                 "Введите 'отмена' для отмены изменения даты" % user.get_date()
        await call.message.edit_text(answer)
        await call.message.answer('Или воспользуйтесь кнопками ниже',
                                  reply_markup=get_fast_keyboard(await fast_date_keyboard(user)))
        await OrderMenu.wait_for_date.set()
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


# Ожидание ввода даты
@dp.message_handler(state=OrderMenu.wait_for_date)
async def wait_date(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("%s Вводит дату: %s" % (user.full_name(), message.text))
    try:
        answer: str = await change_date(user, message.text.lower().strip(" "))
        await message.answer(answer, reply_markup=types.ReplyKeyboardRemove())
        await type_of_selection_message(message)
    except CancelInput:
        await message.answer('Отменён ввод даты.\n', reply_markup=types.ReplyKeyboardRemove())
        user_logger.info("%s Отменяет ввод даты" % user.full_name())
        await state.finish()
    except FutureDate:
        await message.answer("Не всем дано смотреть в завтрашний день\nВведи дату не в будущем")
        return
    except WrongDate:
        await message.answer('Дата введена в неверном формате.')
        return
    await state.finish()


# Ожидание ввода почты
@dp.message_handler(state=OrderMenu.wait_for_email)
async def wait_email(message: types.Message, state: FSMContext):
    user = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("%s Вводит почту: %s" % (user.full_name(), message.text))
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru|[a-z]\d@s-t.studio', message.text):
        user.change_mail(message.text)
        answer = message.from_user.full_name + ', вы установили почту: ' + user.get_email()
        await message.answer(answer)
    elif message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод почты.\n')
        user_logger.info("%s Отменяет ввод почты" % user.full_name())
        await state.finish()
    else:
        await message.answer('Почта введена в неверном формате.\n'
                             'Введите "Отмена" для отмены ввода')
        return
    await state.finish()
    return


# Ожидание ввода предложения замечания
@dp.message_handler(state=OrderMenu.wait_for_offer)
async def wait_offer(message: types.Message, state: FSMContext):
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        user_logger.info("%s Отменяет ввод предложений/замечаний" % message.from_user.full_name)
        await message.answer('Отменён ввод.\n')
        await state.finish()
        return
    user_logger.info("%s Вводит предложений/замечаний: %s" % (message.from_user.full_name, message.text))
    text = ''.join([message.from_user.full_name, ' воспользовался кнопкой предложений/замечаний.\n',
                    '#Отзыв_SMDE_WS_bot\n\n', message.text])
    await bot.send_message(User.get_admin_id(), text)
    await message.answer('Улетело админу, спасибо :)')
    await state.finish()


# Меню выбора способа поиска задачи
@dp.callback_query_handler(callback_menu.filter(action='get tasks list'))
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    user = User.get_user_by_telegram_id(call.from_user.id)
    user_logger.info("%s выбирает способ поиска задачи" % user.full_name())
    buttons = [['Через поиск', 'via search'],
               ['❤️ Через закладки', 'via bookmarks'],
               # ['Ввести id задачи', 'task id input'],
               ['Задача по умолчанию', 'fast input']]
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


# Меню выбора способа поиска задачи
async def type_of_selection_message(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("%s выбирает способ поиска задачи" % user.full_name())
    buttons = [['Через поиск', 'via search'],
               ['❤️ Через закладки', 'via bookmarks'],
               # ['Ввести id задачи', 'task id input'],
               ['Задача по умолчанию', 'fast input']]
    await bot.send_message(user.telegram_id, 'Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


# Выбран способ поиска задачи - введение ID задачи
# @dp.callback_query_handler(callback_menu.filter(action='task id input'))
async def task_id_input(call: types.CallbackQuery, callback_data: dict):
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    user_logger.info("%s выбрал поиск задачи через ввод id задачи" % user.full_name())
    await call.message.edit_text('Введите ID задачи из WorkSection')
    await call.message.answer('Введите "отмена" для отмены ввода', reply_markup=get_fast_keyboard(CANCEL_BUTTON))
    await OrderMenu.waiting_for_task_id.set()


# Ожидание ввода ID задачи
@dp.message_handler(state=OrderMenu.waiting_for_task_id)
async def wait_task_id(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("%s ввёл id задачи: %s" % (user.full_name(), message.text))
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод ID задачи.\n', reply_markup=types.ReplyKeyboardRemove())
        user_logger.info("%s Отменяет ввод ID задачи" % message.from_user.full_name)
        await state.finish()
    try:
        if not re.match(r"(^\d{7,8}$)", message.text):
            raise ValueError
        text = get_text_add_costs(message.text, user)
        await start_comment_input(state, text, user.telegram_id, message.text, message)
    except ValueError:
        await message.answer("Введён некорректный ID задачи")
    except sqlalchemy.exc.NoResultFound:
        await message.answer('Задачи с этим ID нет у меня :С')


# Выбран способ поиска задачи - через поиск
@dp.callback_query_handler(callback_menu.filter(action='via search'))
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    user_logger.info("%s начинает поиск задачи через через поиск. Получил список проектов" % user.full_name())
    user_projects: list[KeyboardData] = await get_project_list(user)
    keyboard = await get_remove_keyboard(user_projects, width=2)
    await call.message.edit_text('Выберите проект', reply_markup=keyboard)


# Выбран способ поиска задачи - через закладки
@dp.callback_query_handler(callback_menu.filter(action='via bookmarks'))
async def search_task_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    user_logger.info("%s выбрал поиск задачи через через закладки" % call.from_user.full_name)
    list_book = get_list_bookmark(call.from_user.id)
    if isinstance(list_book, str):
        await call.message.edit_text(list_book)
        return
    keyboard = await get_remove_keyboard(list_book)
    await call.message.edit_text('Выберите задачу:', reply_markup=keyboard)


# Поиск задачи
@dp.callback_query_handler(callback_remove.filter(action='search_task'))
async def search_tasks_via_search(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_logger.info("%s поиск задачи через поиск. Получает список задач" % call.from_user.full_name)
    project_id: int = int(callback_data['id'])
    await call.message.edit_text('Идёт поиск всех задач. Секундочку подождите')
    try:
        tasks = get_tasks(project_id, int(call.from_user.id))
        if isinstance(tasks, str):
            await start_comment_input(state, tasks, call.from_user.id, callback_data['id'], call)
            return None
        keyboard = await get_remove_keyboard(tasks, width=2)
        await call.message.edit_text('Выберите задачу', reply_markup=keyboard)
    except Exception as e:
        await call.message.edit_text("Ошибка.\nБыло сообщено куда следует.")
        await call.message.answer_sticker("CAACAgIAAxkBAAED9xBiD5m7P2yNcjqvs3y5LhHVJGcfxAACjgADfI5YFQLQ025DM_NRIwQ")
        await bot.send_message(User.get_admin_id(), f"У {call.from_user.full_name} ошибка:\n{e.args}")


# Поиск подзадачи
@dp.callback_query_handler(callback_remove.filter(action='search_subtask'))
async def search_subtasks_via_search(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_logger.info("%s поиск подзадачи через поиск. Получает список подзадач" % call.from_user.full_name)
    parent_task_id: int = int(callback_data['id'])
    await call.message.edit_text('Идёт поиск всех подзадач. Секундочку подождите')
    try:
        tasks = get_subtasks(parent_task_id, int(call.from_user.id))
        if isinstance(tasks, str):
            await start_comment_input(state, tasks, call.from_user.id, callback_data['id'], call)
            return None
        keyboard = await get_remove_keyboard(tasks, width=2)
        await call.message.edit_text('Выберите подзадачу', reply_markup=keyboard)
    except Exception as e:
        await call.message.edit_text("Ошибка.\nБыло сообщено куда следует.")
        await call.message.answer_sticker("CAACAgIAAxkBAAED9xBiD5m7P2yNcjqvs3y5LhHVJGcfxAACjgADfI5YFQLQ025DM_NRIwQ")
        await bot.send_message(User.get_admin_id(), f"У {call.from_user.full_name} ошибка:\n{e.args}")


# Задача выбрана. Запуск ожидания ввода трудоёмкости
@dp.callback_query_handler(callback_remove.filter(action="input_here"))
async def task_found(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_logger.info("%s выбрал задачу" % call.from_user.full_name)
    task_id: int = int(callback_data['id'])
    text = get_text_add_costs(task_id, User.get_user_by_telegram_id(call.from_user.id))
    await start_comment_input(state, text, call.from_user.id, task_id, call)


# Быстрый ввод трудоёмкости
@dp.message_handler(lambda message: message.text.lower() in ["ввести", "add", "внести"])
async def fast_input(message: types.Message, state: FSMContext):
    await message.answer("Да-да?")
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if user.selected_task is None:
        await message.answer('Задача не выбрана, выбери её через поиск')
        return
    text = get_text_add_costs(user.selected_task, user)
    await start_comment_input(state, text, user.telegram_id, user.selected_task, message)


@dp.callback_query_handler(callback_menu.filter(action="fast input"))
async def fast_input_call(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    await call.message.edit_text("Да-да?")
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    if user.selected_task is None:
        await call.message.edit_text('Задача не выбрана, выбери её через поиск')
        return
    text = get_text_add_costs(user.selected_task, user)
    await start_comment_input(state, text, user.telegram_id, user.selected_task, call)


# Вывод текста и клавиатуры по вводу трудоёмкости
async def start_comment_input(state: FSMContext, text: str, user_id: int, task_id: int,
                              call_message: Union[types.CallbackQuery, types.Message]):
    await state.update_data(id=task_id,
                            user_id=user_id)
    if isinstance(call_message, types.CallbackQuery):
        await call_message.message.edit_text(text)
    else:
        await call_message.answer(text)
    await bot.send_message(user_id, 'Варианты доп действий на кнопках:', reply_markup=get_fast_keyboard(TASK_BUTTONS))
    await OrderMenu.waiting_for_time_comment.set()


# Ожидание ввода трудоёмкости
@dp.message_handler(state=OrderMenu.waiting_for_time_comment)
async def wait_hours(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    user_logger.info("%s вводит трудоёмкость" % user.full_name())
    data = await state.get_data()
    text = message.text
    if 'отмена' in text.lower() or 'cancel' in text.lower():
        user_logger.info("%s отменяет ввод трудоёмкости" % user.full_name())
        await message.answer('Отмена ввода', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    elif 'добавить закладку' in text.lower():
        user_logger.info("%s добавляет данную задачу в закладки" % user.full_name())
        task_id = int(data['id'])
        await message.answer(add_bookmark(user.user_id, task_id), reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    elif 'выбрать' in text.lower() or 'select' in text.lower() or 'выбрать по умолчанию' in text.lower():
        user_logger.info("%s выбирает данную задачу задачей по умолчанию" % user.full_name())
        await message.answer(user.change_default_task(int(data['id'])), reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    elif "создать подзадачу" in text.lower():
        project_id = None
        parent_task_id = data.get("id")
        await state.update_data(project_id=project_id,
                                task_id=parent_task_id)
        await message.answer("Введение трудоёмкости отменено", reply_markup=types.ReplyKeyboardRemove())
        await message.answer("Введите название задачи")
        await OrderMenu.wait_for_task_name.set()
    elif "задача выполнена" in text.lower():
        task: Task = Task.get_task(data.get("id"))
        task.complete_task()
        managers: list[User] = [user for user in task.project.users if user.is_manager()]
        await message.answer("Задача выполнена.", reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        for manager in managers:
            try:
                await bot.send_message(manager.telegram_id, f"{user.full_name()} закрыл задачу {task.task_name} "
                                                            f"в проекте {task.project.project_name}")
            except Exception:
                pass
    elif 'ничего не понял' in text.lower() or '!' not in text.lower():
        user_logger.info("%s не понимает что происходит (при вводе трудоёмкости)" % user.full_name())
        await message.answer(INPUT_COST_EXAMPLE)
        return
    else:
        user_logger.info("%s отправил трудоёмкость" % user.full_name())
        for i_status in add_costs(text, data):
            user_logger.info("%s %s" % (user.full_name(), i_status))
            await message.answer(i_status)
        await message.answer('Внесение завершено', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return


# Удаление закладки
@dp.callback_query_handler(callback_remove.filter(action="remove_bookmark"))
async def remove_user_bookmark(call: types.CallbackQuery, callback_data: dict):
    user_logger.info("%s удаляет закладку %s" % (call.from_user.full_name, callback_data['id']))
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    bookmark: Bookmark = Bookmark.get_bookmark_by_id(callback_data['id'])
    user.remove_bookmark(bookmark)
    # remove_bookmark_from_user(callback_data['id'])
    await call.message.edit_text('Закладка удалена')


# Удаление трудоёмкости\ей
@dp.callback_query_handler(callback_remove.filter(action=["remove_cost_ws", "remove_costs"]))  # , "cancel"
async def remove_comments(call: types.CallbackQuery, callback_data: dict):
    user_logger.info("%s удаляет трудоёмкость" % call.from_user.full_name)
    action = callback_data['action']
    if action == "cancel":
        user_logger.info("%s отменяет удаление трудоёмкости" % call.from_user.full_name)
        await call.message.edit_text("Выбор отменён.")
        return
    elif action == "remove_cost_ws":
        cost_id = callback_data["id"]
        status = remove_cost(cost_id)
        user_logger.info("%s получает результат удаления: %s" % (call.from_user.full_name, status))
        await call.message.edit_text(status)
    elif action == "remove_costs":
        user_logger.info("%s удаляет все свои трудоёмкости" % call.from_user.full_name)
        await call.message.edit_text(text_count_removed_costs(call.from_user.id))
        for i_status in remove_costs(User.get_user_by_telegram_id(call.from_user.id)):
            user_logger.info("%s получает результат удаления: %s" % (call.from_user.full_name, i_status))
            await call.message.answer(i_status)
        await call.message.answer('Удаление завершено')
    return


# Меню настроек напоминаний
@dp.callback_query_handler(callback_menu.filter(action='notifications'))
async def setting_notification_menu(call: types.CallbackQuery, callback_data: dict):
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    user_logger.info("%s выбрал кнопку настроек напоминаний" % user.full_name())
    text = get_text_menu_notification(User.notification_status)
    await call.message.edit_text(text, reply_markup=get_keyboard(remind_settings_button, width=1))


# Настройки напоминаний
@dp.callback_query_handler(callback_menu.filter(action=['toggle_notifications', 'Set_notification_time']))
async def setting_notification(call: types.CallbackQuery, callback_data: dict):
    action: str = callback_data["action"]
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    if action == "toggle_notifications":
        user.toggle_notification_status()
        user_logger.info("%s переключил статус напоминаний на %s" % (user.full_name(), user.notification_status))
        status = "Уведомления включены" if user.notification_status else "Уведомления выключены"
        await call.message.edit_text(status)
    elif action == "Set_notification_time":
        user_logger.info("%s запускает ввод времени для уведомлений" % user.full_name())
        await call.message.edit_text("Введите время для уведомлений в формате ЧЧ:MM")
        await OrderMenu.wait_for_notification_time.set()


# Ожидание ввода времени напоминаний
@dp.message_handler(state=OrderMenu.wait_for_notification_time)
async def wait_notification_time(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод времени.\n')
        user_logger.info("%s Отменяет ввод времени" % user.full_name())
        await state.finish()
    elif re.match(r'^(([0-1][0-9])|(2[0-3])):([0-5][0-9])$', message.text):
        in_time = message.text.strip(' ').split(":")
        time: datetime.time = datetime.time(hour=int(in_time[0]), minute=int(in_time[1]))
        user.set_notification_time(time)
        await message.answer(f'Установлено время: {user.notification_time}')
        await state.finish()
    else:
        await message.answer('Время введено в неверном формате. Введите "отмена" для отмены ввода')
        return


@dp.callback_query_handler(callback_remove.filter(action=["create_task", "create_subtask"]))
async def start_create_task(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    action = callback_data.get("action")
    parent_id = callback_data.get("id")
    user_logger.info(f"{user.full_name()} нажимает кнопку {action} при родителе {parent_id}")
    if action == "create_task":
        project_id = parent_id
        parent_task_id = None
    else:
        project_id = None
        parent_task_id = parent_id
    await state.update_data(project_id=project_id,
                            task_id=parent_task_id)
    await call.message.edit_text("Введите название задачи")
    await OrderMenu.wait_for_task_name.set()


@dp.message_handler(state=OrderMenu.wait_for_task_name)
async def read_task_name(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    text = message.text
    user_logger.info(f"{user.full_name()} при создании задачи вводит '{text}'")
    if text.lower() == 'отмена' or text.lower() == 'cancel':
        user_logger.info(f"{user.full_name()} отменил создание задачи")
        await message.edit_text("Создание задачи отменено")
        await state.finish()
        return
    data = await state.get_data()
    await create_task(text, data)
    await message.answer("Задача создана")
    await state.finish()







