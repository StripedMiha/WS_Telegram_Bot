import logging
import re
from typing import Union

import sqlalchemy.exc
from aiogram import Bot, Dispatcher, types
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from app.tgbot.auth import TUser
from app.create_log import setup_logger
from app.tgbot.main import see_days_costs, update_day_costs, about_user, menu_buttons, days_costs_for_remove, remove_costs, \
    remove_cost, text_count_removed_costs, bookmarks_for_remove, remove_bookmark_from_user, get_project_list,\
    get_tasks, get_list_bookmark, add_costs, INPUT_COST_EXAMPLE, add_bookmark, select_task, get_text_add_costs
from app.tgbot.administration.admin_handlers import get_keyboard_admin


bot: Bot
user_logger: logging.Logger = setup_logger("App.Bot.user", "log/user.log")


class OrderMenu(StatesGroup):
    wait_for_email = State()
    waiting_for_task_id = State()
    waiting_for_time_comment = State()
    wait_for_offer = State()
    wait_for_date = State()


def register_handlers_wait_input(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot
    dp.register_message_handler(menu, commands="menu", state="*")
    dp.register_message_handler(wait_offer, state=OrderMenu.wait_for_offer)
    dp.register_message_handler(wait_email, state=OrderMenu.wait_for_email)
    dp.register_message_handler(wait_date, state=OrderMenu.wait_for_date)
    dp.register_message_handler(wait_task_id, state=OrderMenu.waiting_for_task_id)
    dp.register_message_handler(wait_hours, state=OrderMenu.waiting_for_time_comment)


def register_handlers_user(dp: Dispatcher):
    dp.register_message_handler(request_help, commands="help")
    dp.register_message_handler(lets_start, commands="start")
    dp.register_callback_query_handler(choice_cancel, callback_search.filter(action="cancel"))
    dp.register_callback_query_handler(choice_cancel, callback_menu.filter(action="cancel"))
    dp.register_callback_query_handler(menu_action, callback_menu.filter(
        action=['set email', 'change email', 'about me', 'remove book', 'daily report', 'offers', 'change date',
                'remove time cost']))
    dp.register_callback_query_handler(type_of_selection, callback_menu.filter(action='get tasks list'))
    dp.register_callback_query_handler(task_id_input, callback_menu.filter(action='task id input'))
    dp.register_callback_query_handler(search_project_via_search, callback_menu.filter(action='via search'))
    dp.register_callback_query_handler(search_task_via_bookmarks, callback_menu.filter(action='via bookmarks'))
    dp.register_callback_query_handler(search_tasks_via_search, callback_remove.filter(action='search_task'))
    dp.register_message_handler(fast_input,
                                lambda message: message.text.lower() in ["ввести", "add", "внести"])
    dp.register_callback_query_handler(task_found, callback_remove.filter(action="input_here"))
    dp.register_callback_query_handler(remove_user_bookmark, callback_remove.filter(action="remove_bookmark"))
    dp.register_callback_query_handler(remove_comments, callback_remove.filter(
        action=["remove_cost_ws", "remove_costs", "cancel"]))
    dp.register_message_handler(get_dinner, commands="dinner")
    dp.register_message_handler(with_pasta, lambda message_answer: message_answer.text == "С макарошками")
    dp.register_message_handler(with_puree, lambda message_answer: message_answer.text == "С пюрешкой")


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


# Вывод списка команд
async def request_help(message: types.Message):
    user_logger.info("%s %s %s" % (message.from_user.full_name, message.from_user.id, message.text))
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


# Мем версия /start
async def lets_start(message: types.Message):
    user_logger.info("Пользователь %s с id%s ввёл команду /start" % (message.from_user.full_name, message.from_user.id))
    if message.chat.type != 'private':
        user_logger.info("Пользователь %s с id%s пытается запустить бота в групповом чате"
                         % (message.from_user.full_name, message.from_user.id))
        return None
    user = TUser(message.from_user.id, message.from_user.first_name, message.from_user.last_name)
    if user.blocked:
        return None
    elif user.get_status() == 'wait':
        await message.answer('Заявка ушла админу. Ждите.')
        data_for_keyboard = [['Добавить пользователя', 'known_user', user.user_id],
                             ['Игнорировать пользователя', 'black_user', user.user_id]]
        keyboard = get_keyboard_admin(data_for_keyboard, width=2, enable_cancel=False)
        await bot.send_message(int(TUser.get_admin_id()), f"Этот перец пишет мне: {user.full_name}\n"
                                                          f"Пишет вот что: {message.text}", reply_markup=keyboard)
        return None
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{user.first_name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))


# Нажали кнопку отмены
async def choice_cancel(call: types.CallbackQuery):
    user_logger.info("Пользователь %s выбрал отмену" % call.from_user.full_name)
    await call.message.edit_text("Выбор отменён.")
    await call.answer()


# Ввели команду /menu
async def menu(message: types.Message):
    user = TUser(message.from_user.id)
    user_logger.info("Пользователь %s ввёл команду /menu" % user.full_name)
    if not user.has_access:
        return None
    buttons = menu_buttons(user)
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))
    await update_day_costs(user)


# Нажали кнопку в меню
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    user = TUser(call.from_user.id)
    user_logger.info("%s выбрал кнопку %s" % (user.full_name, action))
    date = 'сегодня' if user.get_date() == 'today' else user.get_date()
    if action == 'set email':  # or action == 'change email':
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
                 "Введите 'отмена' для отмены изменения даты"
        await call.message.edit_text(answer)
        await call.message.answer('Или воспользуйтесь кнопками ниже', reply_markup=get_fast_keyboard(DATE_BUTTONS))
        await OrderMenu.wait_for_date.set()
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


# Ожидание ввода даты
async def wait_date(message: types.Message, state: FSMContext):
    user = TUser(message.from_user.id)
    user_logger.info("%s Вводит дату: %s" % (user.full_name, message.text))
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод даты.\n', reply_markup=types.ReplyKeyboardRemove())
        user_logger.info("%s Отменяет ввод даты" % user.full_name)
        await state.finish()
    elif message.text.lower() == 'сегодня' or message.text.lower() == 'today':
        user.change_date('today')
        await message.answer('Теперь бот будет записывать на текущий день', reply_markup=types.ReplyKeyboardRemove())
    elif message.text.lower() == 'вчера' or message.text.lower() == 'yesterday':
        user.change_date('yesterday')
        await message.answer('Установлена вчерашняя дата', reply_markup=types.ReplyKeyboardRemove())
    elif re.match(r'(((0[1-9])|([1-2][0-9])|(3[0-1]))[., :]((0[1-9])|(1[0-2]))[., :]20[2-9][0-9])', message.text):
        date = message.text.strip(' ')
        user.change_date(date)
        await message.answer(f'Установлена дата: {user.get_date()}', reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer('Дата введена в неверном формате.')
        return
    await state.finish()
    return


# Ожидание ввода почты
async def wait_email(message: types.Message, state: FSMContext):
    user = TUser(message.from_user.id)
    user_logger.info("%s Вводит почту: %s" % (user.full_name, message.text))
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru|[a-z]\d@s-t.studio', message.text):
        user.change_mail(message.text)
        answer = message.from_user.full_name + ', вы установили почту: ' + user.get_email()
        await message.answer(answer)
    elif message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод почты.\n')
        user_logger.info("%s Отменяет ввод почты" % user.full_name)
        await state.finish()
    else:
        await message.answer('Почта введена в неверном формате.\n'
                             'Введите "Отмена" для отмены ввода')
        return
    await state.finish()
    return


# Ожидание ввода предложения замечания
async def wait_offer(message: types.Message, state: FSMContext):
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        user_logger.info("%s Отменяет ввод предложений/замечаний" % message.from_user.full_name)
        await message.answer('Отменён ввод.\n')
        await state.finish()
        return
    user_logger.info("%s Вводит предложений/замечаний: %s" % (message.from_user.full_name, message.text))
    text = ''.join([message.from_user.full_name, ' воспользовался кнопкой предложений/замечаний.\n',
                    '#Отзыв_SMDE_WS_bot\n\n',  message.text])
    await bot.send_message(TUser.get_admin_id(), text)
    await message.answer('Улетело админу, спасибо :)')
    await state.finish()


# Меню выбора способа поиска задачи
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    user_logger.info("%s выбирает способ поиска задачи" % user.full_name)
    buttons = [['Через поиск', 'via search'],
               ['❤️ Через закладки', 'via bookmarks'],
               ['Ввести id задачи', 'task id input']]
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))


# Выбран способ поиска задачи - введение ID задачи
async def task_id_input(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    user_logger.info("%s выбрал поиск задачи через ввод id задачи" % user.full_name)
    await call.message.edit_text('Введите ID задачи из WorkSection')
    await call.message.answer('Введите "отмена" для отмены ввода', reply_markup=get_fast_keyboard(CANCEL_BUTTON))
    await OrderMenu.waiting_for_task_id.set()


# Ожидание ввода ID задачи
async def wait_task_id(message: types.Message, state: FSMContext):
    user = TUser(message.from_user.id)
    user_logger.info("%s ввёл id задачи: %s" % (user.full_name, message.text))
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод ID задачи.\n', reply_markup=types.ReplyKeyboardRemove())
        user_logger.info("%s Отменяет ввод ID задачи" % message.from_user.full_name)
        await state.finish()
    try:
        if not re.match(r"(^\d{7,8}$)", message.text):
            raise ValueError
        text = get_text_add_costs(message.text, user)
        await start_comment_input(state, text, user.user_id, message.text, message)
    except ValueError:
        await message.answer("Введён некорректный ID задачи")
    except sqlalchemy.exc.NoResultFound:
        await message.answer('Задачи с этим ID нет у меня :С')


# Выбран способ поиска задачи - через поиск
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    user = TUser(call.from_user.id)
    user_logger.info("%s начинает поиск задачи через через поиск. Получил список проектов" % user.full_name)
    user_projects = await get_project_list(user)
    keyboard = await get_remove_keyboard(user_projects, width=2)
    await call.message.edit_text('Выберите проект', reply_markup=keyboard)


# Выбран способ поиска задачи - через закладки
async def search_task_via_bookmarks(call: types.CallbackQuery, callback_data: dict):
    user_logger.info("%s выбрал поиск задачи через через закладки" % call.from_user.full_name)
    list_book = get_list_bookmark(call.from_user.id)
    if isinstance(list_book, str):
        await call.message.edit_text(list_book)
        return
    keyboard = await get_remove_keyboard(list_book)
    await call.message.edit_text('Выберите задачу:', reply_markup=keyboard)


# Поиск задачи
async def search_tasks_via_search(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_logger.info("%s поиск задачи через через закладки. Получает список задач/подзадач" % call.from_user.full_name)
    project_id = callback_data['id']
    await call.message.edit_text('Идёт поиск всех задач. Секундочку подождите')
    tasks = get_tasks(project_id, call.from_user.id)
    if isinstance(tasks, str):
        await start_comment_input(state, tasks, call.from_user.id, callback_data['id'], call)
        return None
    keyboard = await get_remove_keyboard(tasks, width=2)
    await call.message.edit_text('Выберите задачу', reply_markup=keyboard)


# Задача выбрана. Запуск ожидания ввода трудоёмкости
async def task_found(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    user_logger.info("%s выбрал задачу" % call.from_user.full_name)
    task_id = callback_data['id']
    text = get_text_add_costs(task_id, TUser(call.from_user.id))
    await start_comment_input(state, text, call.from_user.id, task_id, call)


# Быстрый ввод трудоёмкости
async def fast_input(message: types.Message, state: FSMContext):
    await message.answer("Да-да?")
    user = TUser(message.from_user.id)
    if user.selected_task is None:
        await message.answer('Задача не выбрана, выбери её через поиск')
        return
    text = get_text_add_costs(user.selected_task, user)
    await start_comment_input(state, text, user.user_id, user.selected_task, message)


# Вывод текста и клавиатуры по вводу трудоёмкости
async def start_comment_input(state: FSMContext, text: str, user_id: int, task_id: str,
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
async def wait_hours(message: types.Message, state: FSMContext):
    user = TUser(message.from_user.id)
    user_logger.info("%s вводит трудоёмкость" % user.full_name)
    data = await state.get_data()
    text = message.text
    if 'отмена' in text.lower() or 'cancel' in text.lower():
        user_logger.info("%s отменяет ввод трудоёмкости" % user.full_name)
        await message.answer('Отмена ввода', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    elif 'добавить закладку' in text.lower():
        user_logger.info("%s добавляет данную задачу в закладки" % user.full_name)
        task_id = data['id']
        await message.answer(add_bookmark(user.user_id, task_id), reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
    elif 'выбрать' in text.lower() or 'select' in text.lower() or 'выбрать по умолчанию' in text.lower():
        user_logger.info("%s выбирает данную задачу задачей по умолчанию" % user.full_name)
        await message.answer(select_task(user.user_id, data['id']), reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return
    elif 'ничего не понял' in text.lower() or '!' not in text.lower():
        user_logger.info("%s не понимает что происходит (при вводе трудоёмкости)" % user.full_name)
        await message.answer(INPUT_COST_EXAMPLE, reply_markup=types.ReplyKeyboardRemove())
        return
    else:
        user_logger.info("%s отправил трудоёмкость" % user.full_name)
        for i_status in add_costs(text, data):
            user_logger.info("%s %s" % (user.full_name, i_status))
            await message.answer(i_status)
        await message.answer('Внесение завершено', reply_markup=types.ReplyKeyboardRemove())
        await state.finish()
        return


# Удаление закладки
async def remove_user_bookmark(call: types.CallbackQuery, callback_data: dict):
    user_logger.info("%s удаляет закладку %s" % (call.from_user.full_name, callback_data['id']))
    remove_bookmark_from_user(callback_data['id'])
    await call.message.edit_text('Закладка удалена')


# Удаление трудоёмкости\ей
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
        for i_status in remove_costs(TUser(call.from_user.id)):
            user_logger.info("%s получает результат удаления: %s" % (call.from_user.full_name, i_status))
            await call.message.answer(i_status)
        await call.message.answer('Удаление завершено')
    return


# Выбор обеда с клавиатуры
async def get_dinner(message: types.Message):
    user = TUser(message.from_user.id)
    if not user.has_access:
        if user.get_status() == 'black' or user.get_status == 'wait':
            return None
        await message.answer('Нет доступа\nНапиши /start в личку боту, чтобы запросить доступ')
        return None
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["С пюрешкой", "С макарошками", " отмена"]
    keyboard.add(*buttons)
    await message.answer("Как подавать котлеты?", reply_markup=keyboard)


# Обработка ответа выбора обеда
async def with_pasta(message_answer: types.Message):
    await message_answer.answer_photo(
        'https://otvet.imgsmail.ru/download/214880555_ab5a400b4f358b8003dcdd86d4186d58_800.jpg',
        reply_markup=types.ReplyKeyboardRemove())


async def with_puree(message_answer: types.Message):
    await message_answer.answer("Ням-ням", reply_markup=types.ReplyKeyboardRemove())

