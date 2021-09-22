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
from app.auth import *
from ws_api import get_all_project_for_user, get_tasks, search_tasks, get_format_today_costs, remove_cost, add_cost, \
    get_task_info, check_task_name
from app.fun import register_handlers_fun

from pprint import pprint
from contextlib import suppress
from random import randint

config = load_config("config/bot.ini")
# token = '1909941584:AAHRt33_hZPH9XzGRbQpAyqGzh9sbwEWZtQ'
bot = Bot(token=config.tg_bot.token, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())


class OrderMenu(StatesGroup):
    wait_for_email = State()
    waiting_for_time_comment = State()
    wait_for_offer = State()
    wait_news = State()
    wait_for_date = State()


def register_handlers_time_cost(dp: Dispatcher):
    dp.register_message_handler(menu, commands="menu", state="*")
    dp.register_message_handler(wait_offer, state=OrderMenu.wait_for_offer)
    dp.register_message_handler(wait_email, state=OrderMenu.wait_for_email)
    dp.register_message_handler(wait_date, state=OrderMenu.wait_for_date)
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


callback_ad = CallbackData("fab_num", "id_user", "action", "full_name")


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
    log_in(message.from_user.id, message.from_user.full_name, message.text)
    if message.chat.type != 'private':
        log_in(message.from_user.full_name, 'не прав')
        return None
    if not check_user(message.from_user.id):
        if check_user(message.from_user.id, 'black'):
            return None
        if check_user(message.from_user.id, 'wait'):
            return None
        await message.answer('Заявка ушла админу. Ждите.')
        if message.from_user.last_name is None:
            last_name = 'Snow'
        else:
            last_name = message.from_user.last_name
        new_user_data = [message.from_user.id, message.from_user.first_name, last_name,
                         message.chat.type]
        new_user(new_user_data)
        buttons = [types.InlineKeyboardButton(text='Добавить пользователя',
                                              callback_data=callback_ad.new(
                                                  action='add_user',
                                                  id_user=message.from_user.id,
                                                  full_name=message.from_user.full_name
                                              )),
                   types.InlineKeyboardButton(text='Игнорировать пользователя',
                                              callback_data=callback_ad.new(
                                                  action='ignore_user',
                                                  id_user=message.from_user.id,
                                                  full_name=message.from_user.full_name
                                              ))]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await bot.send_message(300617281, f"Этот перец пишет мне: {message.from_user.full_name}\n"
                                          f"Пишет вот что: {message.text}", reply_markup=keyboard)
        return None
    answer = [f"Наталья, морская пехота",
              f"Стартуем, <i>{message.from_user.first_name}!</i>",
              f"Введи /help чтобы получить список команд"
              ]
    await message.answer_photo('https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg', caption='\n'.join(answer))


@dp.callback_query_handler(callback_ad.filter(action=['add_user', 'ignore_user']))
async def user_decide(call: types.CallbackQuery, callback_data: dict):
    action = callback_data['action']
    full_name = callback_data['full_name']
    if action == "add_user":
        change_list(callback_data['id_user'], 'wait', 'user')
        await call.answer(text='Пользователь добавлен', show_alert=True)
        await call.answer()
        await call.message.edit_text(f"Пользователь {full_name} добавлен")
        await bot.send_message(callback_data['id_user'], 'Доступ разрешён.')
        answer = [f"Наталья, морская пехота",
                  f"Стартуем, <i>{full_name.split(' ')[0]}!</i>",
                  f"Введи /help чтобы получить список команд"
                  ]
        await bot.send_photo(callback_data['id_user'], 'https://pbs.twimg.com/media/Dui9iFPXQAEIHR5.jpg',
                             caption='\n'.join(answer))
    elif action == "ignore_user":
        change_list(callback_data['id_user'], 'wait', 'black')
        await call.answer(text='Пользователь добавлен в чёрный список', show_alert=True)
        await call.message.edit_text(
            f'Пользователь {full_name} добавлен в чёрный список')
        await bot.send_message(callback_data['id_user'], 'Вас добавили в чёрный список')


@dp.callback_query_handler(callback_ad.filter(action='cancel'))
async def ad_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text('Выбор отменён')
    await state.finish
    await call.answer()


@dp.message_handler(commands="change_status")
async def status_changer(message: types.Message):
    if not check_admin(message.from_user.id):
        return None
    buttons = [types.InlineKeyboardButton(text='Пользователи',
                                          callback_data=callback_ad.new(
                                              action='list_user',
                                              id_user='   ',
                                              full_name='   '
                                          )),
               types.InlineKeyboardButton(text='Заблокированные',
                                          callback_data=callback_ad.new(
                                              action='list_black',
                                              id_user='  ',
                                              full_name='  '
                                          )),
               types.InlineKeyboardButton(text='Отмена',
                                          callback_data=callback_ad.new(
                                              action='cancel',
                                              id_user='  ',
                                              full_name='  '
                                          ))]
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    await message.answer('Выбери список для поиска пользователя, которому хочешь изменить статус',
                         reply_markup=keyboard)


@dp.callback_query_handler(callback_ad.filter(action=['list_user', 'list_black']))
async def select_list(call: types.callback_query, callback_data: dict):
    selected_list = callback_data['action'].split('_')[1]
    users = get_list(selected_list)
    buttons = []
    for i, j in users.items():
        buttons.append(types.InlineKeyboardButton(text=j,
                                                  callback_data=callback_ad.new(
                                                      action=selected_list,
                                                      id_user=i,
                                                      full_name=j
                                                  )))
    buttons.append(types.InlineKeyboardButton(text='Отмена',
                                              callback_data=callback_ad.new(
                                                  action='cancel',
                                                  id_user='  ',
                                                  full_name='  '
                                              )))
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    await call.message.edit_text('Выберите пользователя:',
                                 reply_markup=keyboard)


@dp.callback_query_handler(callback_ad.filter(action=['user', 'black']))
async def select_user(call: types.callback_query, callback_data: dict):
    selected_list = callback_data.get('action')
    id_of = callback_data.get('id_user')
    name = callback_data['full_name']
    if selected_list == 'user':
        answer = f'Пользователь {name} удалён из списка пользователей.'
        another_list = 'black'
    else:
        answer = f'Пользователь {name} удалён из чёрного списка.'
        another_list = 'user'
    log_in(name, 'del from', selected_list)
    change_list(id_of, selected_list, another_list)
    await call.message.edit_text(answer)
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
    log_in(call.from_user.full_name, 'cancel')
    await call.message.edit_text("Выбор отменён.")
    await call.answer()


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),

    ]
    await bot.set_my_commands(commands)


async def menu(message: types.Message):
    log_in(message.from_user.full_name, message.text)
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
        if check_mail(message.from_user.id, 'date') == 'today':
            date = 'сегодня'
        else:
            date = check_mail(message.from_user.id, 'date')
        buttons = {'daily report': f"📃 Отчёт за {date}",
                   'search task': '🔍 Найти задачу',
                   'remove time cost': '❌🕓 Удалить трудочасы',
                   'remove book': '❌🧷 Удалить закладку',
                   'change date': '🔄📅 Изменить дату',
                   'change email': '🔄📧 Изменить почту',
                   'about me': 'ℹ️ О вас',
                   'offers': '💬 Предложение/отзыв'}
    await message.answer('Доступные действия:', reply_markup=get_keyboard(buttons, 2))


callback_remove = CallbackData("fab_task", "page", "id", "action")


@dp.callback_query_handler(callback_fd.filter(action=['set email', 'change email', 'about me', 'remove book',
                                                      'daily report', 'remove time cost', 'offers', 'change date']))
async def menu_action(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data.get('action')
    log_in(call.from_user.full_name, action)
    if action == 'set email':  # or action == 'change email':
        await call.message.edit_text('Введите вашу корпоративную почту:\n'
                                     'Введите "Отмена" для отмены ввода')
        await OrderMenu.wait_for_email.set()
    elif action == 'about me':
        user_dict = read_json('user').get(str(call.from_user.id))
        status = 'Администратор' if check_admin(str(call.from_user.id)) else 'Пользователь'
        answer = f"Ваше имя - {user_dict['first_name']} {user_dict['last_name']}\n" + \
                 f"Ваша почта - {user_dict.get('email')}\n" + \
                 f"Ваш статус - {status}\n" + \
                 f"Указанная дата - {check_mail(call.from_user.id, 'date')}"
        await call.message.edit_text(answer)
    elif action == 'daily report':
        answer = get_format_today_costs(check_mail(call.from_user.id), date=check_mail(call.from_user.id, 'date'))
        if answer is None:
            await call.message.edit_text(f"Вы не внесли трудоёмкости за {check_mail(call.from_user.id, 'date')}.\n"
                                         'Не навлекай на себя гнев Ксении. \n'
                                         'Будь умничкой - внеси часы.')
            return
        if check_mail(call.from_user.id, 'date') == 'today':
            date = 'сегодня'
        else:
            date = check_mail(call.from_user.id, 'date')
        await call.message.edit_text(f"<b>Отчёт за {date}:</b>\n\n")
        await call.message.answer(answer)
    elif action == 'remove time cost':
        comment = get_format_today_costs(check_mail(str(call.from_user.id)), True,
                                         check_mail(call.from_user.id, 'date'))
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
        user_book = read_json('user').get(str(call.from_user.id)).get('bookmarks')
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
    elif action == 'change date':
        answer = "Введите дату в формате ДД.ММ.ГГГГ:\n" \
                 "Введите 'сегодня' или 'today', чтобы бот взаимодействовал с днём который будет на тот" \
                 " момент сегодняшним 🤪\n" \
                 "Введите 'отмена' для отмены изменения даты"
        await call.message.edit_text(answer)
        await OrderMenu.wait_for_date.set()
    else:
        await call.message.edit_text('Пока ниработает :с')
    await call.answer()
    return None


async def wait_date(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, 'Вводит дату:', message.text)
    if message.text.lower() == 'отмена' or message.text.lower() == 'cancel':
        await message.answer('Отменён ввод даты.\n')
        log_in(message.from_user.full_name, 'cancel input date')
        await state.finish()
    elif message.text.lower() == 'сегодня' or message.text.lower() == 'today':
        edit_data(message.from_user.id, 'today', 'date')
        await message.answer('Теперь бот будет записывать на текущий день')
    elif re.match(r'(((0[1-9])|([1-2][0-9])|(3[0-1]))\.((0[1-9])|(1[0-2]))\.20[2-9][0-9])', message.text):
        date = message.text.strip(' ')
        edit_data(message.from_user.id, date, 'date')
        await message.answer(f'Установлена дата: {date}')
    else:
        await message.answer('Дата введена в неверном формате.')
        return
    await state.finish()
    return


async def wait_email(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    if re.match(r'[a-zA-Z]\.[a-z]{3,15}@smde\.ru|[a-z]\d@s-t.studio', message.text):
        edit_data(message.from_user.id, message.text, 'email')
        answer = message.from_user.full_name + ', вы установили почту: ' + check_mail(message.from_user.id)
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
    await bot.send_message(300617281, text)
    await message.answer('Улетело админу, спасибо :)')
    await state.finish()


@dp.callback_query_handler(callback_fd.filter(action=['search task']))
async def type_of_selection(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, check_mail(str(call.from_user.id)), '- add time cost')
    buttons = {'via search': 'Через поиск', 'via bookmarks': '❤️ Через закладки'}
    await call.message.edit_text('Как будем искать задачу:', reply_markup=get_keyboard(buttons, 2))

callback_search = CallbackData('fab_search', 'action', 'path')


@dp.callback_query_handler(callback_fd.filter(action=['via search']))
async def search_project_via_search(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    user_email = read_json('user').get(str(call.from_user.id)).get('email')
    if user_email is not None:
        user_projects = get_all_project_for_user(user_email)
    # user_data[call.from_user.id] = {'path': '/project/'}
    buttons = []
    for i, j in user_projects.items():
        buttons.append(types.InlineKeyboardButton(text=j,
                                                  callback_data=callback_search.new(action='search_task',
                                                                                    path=f'/project/{i}/',
                                                                                    )))
    buttons.append(types.InlineKeyboardButton(text='Отмена', callback_data=callback_search.new(action='cancel',
                                                                                        path=' ')))
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    await call.message.edit_text('Выберите проект', reply_markup=keyboard)


@dp.callback_query_handler(callback_search.filter(action="cancel"))
async def remove_comments(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    await call.message.edit_text("Выбор отменён")
    return


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
                                                                                        id='---',
                                                                                        action="add_costs")))
        buttons.append(types.InlineKeyboardButton(text='Отмена',
                                                  callback_data=callback_remove.new(page="---",
                                                                                    id="---",
                                                                                    action="cancel")))
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)
        await call.message.edit_text('Выберите задачу:', reply_markup=keyboard)
    return


@dp.callback_query_handler(callback_search.filter(action='search_task'))
async def search_tasks_via_search(call: types.CallbackQuery, callback_data: dict):
    log_in(call.from_user.full_name, call['data'])
    path = callback_data['path']
    tasks = search_tasks(path)
    buttons = []
    for i, j in tasks.items():
        buttons.append(types.InlineKeyboardButton(text=j.get('name'),
                                                  callback_data=callback_search.new(action='search_subtask',
                                                                                    path=f'{path}{i}/')))
    buttons.append(types.InlineKeyboardButton(text='Отмена',
                                              callback_data=callback_search.new(action='cancel', path=' ')))
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    await call.message.edit_text('Выберите задачу', reply_markup=keyboard)


INPUT_COSTS = """
Введите часы и описание деятельности:
Можно ввести в одну строку, можно в несколько(но в одном сообщении).
В начале указываете количество часов, следом через '!' можно перечислить один или несколько комментариев.
Можно ввести больше двух часов. Алгоритм сам разделит по два часа. Пробелы между '!' не важны

Для отмены введите '<i>отмена</i>'
Для более подробного описания введите '<i>Ничего не понял</i>'
Для добавления задачи в закладки введите '<i>Добавить закладку</i>'
Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> ! <i>Сборка печатного прототипа</i>
"""
# "\n\n"
# "Пример№2:\n<i>0.5</i>! <i>Печать деталей корпуса</i> \n"
# "<i>2.5</i>! <i>Сборка печатного прототипа</i>\n\n"
# "В первом примере в бот разделит указанное количество часов на количество задач,"
# "в данном случае в WS улетит две записи по полтора часа.\n"
# "Во втором примере в WS улетит 3 записи:\n"
# "Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся "
# "на две записи: на запись с двумя часами и запись с получасом."
# """


@dp.callback_query_handler(callback_search.filter(action='search_subtask'))
async def search_subtasks_via_search(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    log_in(call.from_user.full_name, call['data'])
    path = callback_data['path']
    id = path.split('/')[-2]
    project_tasks = search_tasks(path)
    if project_tasks.get(id) is None or project_tasks.get(id).get('child') is None:
        await state.update_data(path=callback_data['path'])
        name = check_task_name(path)
        date = 'Установленная дата - ' + check_mail(call.from_user.id, 'date') + '\n'
        answer = name + date + INPUT_COSTS
        await call.message.edit_text(answer)
        await OrderMenu.waiting_for_time_comment.set()
        return
    buttons = []
    for i, j in project_tasks.get(id).get('child').items():
        buttons.append(types.InlineKeyboardButton(text=j.get('name'),
                                                  callback_data=callback_search.new(action='search_subtask',
                                                                                    path=f'{path}{i}/')))
    buttons.append(types.InlineKeyboardButton(text='Отмена',
                                              callback_data=callback_search.new(action='cancel', path=' ')))
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    await call.message.edit_text('Выберите подзадачу', reply_markup=keyboard)


@dp.callback_query_handler(callback_remove.filter(action=["add_costs"]))
async def add_costs_via_bookmarks(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    log_in(call.from_user.full_name, call['data'])
    task_info = get_task_info(callback_data['page'])
    await state.update_data(path=task_info.get('data').get('page'))
    task_name = task_info['data']['project']['name'] + ' // ' + task_info['data']['name'] + '\n'
    date = 'Установленная дата - ' + check_mail(call.from_user.id, 'date') + '\n'
    answer = task_name + date + INPUT_COSTS  # todo имя проекта и задачи в сообщении\
    await call.message.edit_text(answer)
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
        comments = get_format_today_costs(check_mail(str(call.from_user.id)), True,
                                          check_mail(str(call.from_user.id), 'date'))
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


async def add_costs(text, id_user, path):
    email = check_mail(str(id_user))
    full_name = check_mail(id_user, 'first_name') + ' ' + check_mail(id_user, 'last_name')
    for string in text.split('\n'):
        time_str = string.split('!')[0]
        if ':' in time_str:
            min = int(time_str.split(':')[1])
            hours = int(time_str.split(':')[0])
            if min >= 60:
                hours += min // 60
                min = min % 60
                print(min)
            min10 = int(min * 100 / 60)
            if min < 6:
                time_str = str(hours) + '.0' + str(min10)
            else:
                time_str = str(hours) + '.' + str(min10)
        time = float(time_str.replace(',', '.') if ',' in time_str else time_str)
        comment = [i.strip(' ') for i in string.split('!')[1:]]  # Удаление пробелов в начале и концекаждой задачи
        if '' in comment:
            comment.remove('')
        for i in comment:
            comment_time = time / len(comment)
            if comment_time > 2:
                q_time = comment_time
                while q_time > 2:
                    q_time -= 2
                    status = add_cost(path, email, i, 2, check_mail(id_user, 'date'))
                    if status == 'ok':
                        log_in(full_name, 'add comments', path, email, i, 2, check_mail(id_user, 'date'))
                        answer = 'Успешно внесено'
                    else:
                        answer = 'Не успех'
                    await bot.send_message(int(id_user), answer)
                status = add_cost(path, email, i, q_time, check_mail(id_user, 'date'))
                if status == 'ok':
                    log_in(full_name, 'add comments', path, email, i, q_time, check_mail(id_user, 'date'))
                    answer = 'Успешно внесено'
                else:
                    answer = 'Не успех'
                await bot.send_message(int(id_user), answer)
            else:
                status = add_cost(path, email, i, comment_time, check_mail(id_user, 'date'))
                if status == 'ok':
                    log_in(full_name, 'add comments', path, email, i, comment_time, check_mail(id_user, 'date'))
                    answer = 'Успешно внесено'
                else:
                    answer = 'Не успех'
                await bot.send_message(int(id_user), answer)
        answer2 = '<b>Время</b> - ' + str(time) + 'ч\n<b>Проделанная работа</b> - ' + ', '.join(comment)
        await bot.send_message(int(id_user), answer2)


async def wait_hours(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, message.text)
    data = await state.get_data()
    text = message.text
    if 'отмена' in text.lower() or 'cancel' in text.lower():
        await message.answer('Отмена ввода')
        await state.finish()
        return
    if 'добавить закладку' in text.lower():
        path = data['path']
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
                log_in(message.from_user.full_name, 'bookmark added')
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
        await message.answer("Дробную и целую часть часа можно разделить '.', ','"
                             "Если использовать ':', то будет взято точно указанное количество минут"
                             "Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> !"
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
    await add_costs(text, message.from_user.id, data['path'])
    await state.finish()


@dp.message_handler(commands='news')
async def wait_for_news(message: types.Message):
    log_in(message.from_user.full_name, 'send news')
    if check_admin(message.from_user.id) is None:
        return None
    await message.answer('Введите новость:')
    await OrderMenu.wait_news.set()
    return


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


async def news_to_users(message: types.Message, state: FSMContext):
    log_in(message.from_user.full_name, 'send news')
    if not check_admin(message.from_user.id):
        return None
    users = read_json('user')
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
