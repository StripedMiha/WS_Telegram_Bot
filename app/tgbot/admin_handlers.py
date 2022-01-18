import logging

import aiogram.utils.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import IDFilter
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from app.KeyboardDataClass import KeyboardData
from app.create_log import setup_logger
from app.tgbot.main import get_users_of_list
from app.tgbot.auth import TUser


bot: Bot
admin_logger: logging.Logger = setup_logger("App.Bot.admin", "app/log/admin.log")


class OrderMenu(StatesGroup):
    wait_news = State()


callback_auth = CallbackData("fab_auth", "data", "action")


def register_handlers_admin(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot
    dp.register_message_handler(status_changer, IDFilter(user_id=admin_id), commands="change_status")
    dp.register_message_handler(wait_for_news, IDFilter(user_id=admin_id), commands='news')
    dp.register_message_handler(log_for_admin, IDFilter(user_id=admin_id), commands='log')
    dp.register_callback_query_handler(user_decide, IDFilter(user_id=admin_id),
                                       callback_auth.filter(action=['known_user', 'black_user']))
    dp.register_callback_query_handler(add_cancel, IDFilter(user_id=admin_id), callback_auth.filter(action='cancel'))
    dp.register_callback_query_handler(select_list, IDFilter(user_id=admin_id),
                                       callback_auth.filter(action=['list_user', 'list_black']))
    dp.register_message_handler(news_to_users, IDFilter(user_id=admin_id), state=OrderMenu.wait_news)


def get_keyboard_admin(list_data: list[KeyboardData], width: int = 1, enable_cancel: bool = True) \
        -> types.InlineKeyboardMarkup:
    buttons = []
    for i in list_data:
        buttons.append(types.InlineKeyboardButton(text=i.text,
                                                  callback_data=callback_auth.new(action=i.action,
                                                                                  data=i.id)))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_auth.new(action="cancel",
                                                                                                 data='   ')))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


LIST_ATTRIBUTES: dict = {
    "known_user": {
        "new_status": "user",
        "text_for_admin": "Пользователь %s добавлен",
        "text_for_alarm": "Пользователь добавлен",
        "text_for_user": "Доступ разрешён. \nВведите /start чтобы начать."
    },
    "black_user": {
        "new_status": "black",
        "text_for_admin": "Пользователь %s добавлен в чёрный список",
        "text_for_alarm": "Пользователь добавлен в чёрный список",
        "text_for_user": "Вас добавили в чёрный список"
    }
}


async def user_decide(call: types.CallbackQuery, callback_data: dict):
    case = callback_data['action']
    user = TUser(callback_data['data'])
    admin_logger.info("%s выбрал %s для переноса в список %s" % (call.from_user.full_name, user.full_name, case))
    user.change_status(LIST_ATTRIBUTES[case]["new_status"])
    await call.answer(LIST_ATTRIBUTES[case]["text_for_alarm"], show_alert=True)
    await call.answer()
    await call.message.edit_text(LIST_ATTRIBUTES[case]["text_for_admin"] % user.full_name)
    try:
        await bot.send_message(user.user_id, LIST_ATTRIBUTES[case]["text_for_user"])
        admin_logger.info("%s получил уведомление о смене статуса" % user.full_name)
    except aiogram.utils.exceptions.ChatNotFound:
        await bot.send_message(TUser.get_admin_id(),
                               'Пользователь не получил уведомления, так как не имеет диалога с ботом')
        admin_logger.info("%s НЕ получил уведомление о смене статуса" % user.full_name)


async def add_cancel(call: types.CallbackQuery, state: FSMContext):
    admin_logger.info("%s Жмёт отмену" % call.from_user.full_name)
    await call.message.edit_text('Выбор отменён.')
    await state.finish()
    await call.answer()


async def status_changer(message: types.Message):
    admin_logger.info("%s запрашивает списки пользователей" % message.from_user.full_name)
    data_for_keyboard = [KeyboardData('Пользователи', 0, 'list_user'),
                         KeyboardData('Заблокированные',  0, 'list_black')]
    keyboard = get_keyboard_admin(data_for_keyboard)
    await message.answer('Выбери список для поиска пользователя, которому хочешь изменить статус',
                         reply_markup=keyboard)


async def select_list(call: types.CallbackQuery, callback_data: dict):
    selected_list = callback_data['action'].split('_')[1]
    admin_logger.info("%s запрашивает список %s" % (call.from_user.full_name, selected_list))
    keyboard = get_keyboard_admin(get_users_of_list(selected_list), width=2)
    await call.message.edit_text('Выберите пользователя:', reply_markup=keyboard)


async def wait_for_news(message: types.Message):
    admin_logger.info("%s вводит новость" % message.from_user.full_name)
    await message.answer('Введите новость:')
    await OrderMenu.wait_news.set()
    return


async def news_to_users(message: types.Message, state: FSMContext):
    admin_logger.info("%s отправил новость" % message.from_user.full_name)
    users: list[list[str, int]] = [[i.text, i.id] for i in get_users_of_list('user')]
    for name, user_id in users:
        news = message.text
        text = f'{name}, Это новости бота 🙃\n\n{news}'
        try:
            await bot.send_message(user_id, text)
            admin_logger.info("%s получил новость" % name)
        except aiogram.utils.exceptions.ChatNotFound:
            admin_logger.error("%s НЕ получил новость" % name)
        except aiogram.utils.exceptions.BotBlocked:
            admin_logger.error("%s заблокировал бота" % name)
    await state.finish()
    await message.answer('Отправлено')


async def log_for_admin(message: types.Message):
    admin_logger.info("admin %s request %s" % (message.from_user.full_name, message.text))
    try:
        count = int(message.text.split(' ')[2])
        log_name = message.text.split(' ')[1]
    except IndexError:
        count = int(message.text.split(' ')[-1])
        log_name = 'app'
    try:
        with open(f'app/log/{log_name}.log', 'r', encoding='utf-8') as f:
            text = f.readlines()[-count:]
    except FileNotFoundError:
        await message.answer('Не верное имя лога')
        return
    answer = ''.join(text)
    await message.answer(answer)
