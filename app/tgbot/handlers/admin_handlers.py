import logging

import aiogram.utils.exceptions
from aiogram import types
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext

from app.KeyboardDataClass import KeyboardData
from app.create_log import setup_logger
from app.db.structure_of_db import User, Status
from app.back.main import get_users_of_list
from app.tgbot.loader import dp, bot

admin_logger: logging.Logger = setup_logger("App.Bot.admin", "app/log/admin.log")


class OrderMenu(StatesGroup):
    wait_news = State()


callback_auth = CallbackData("fab_auth", "data", "action")


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
    "blocked_user": {
        "new_status": "blocked",
        "text_for_admin": "Пользователь %s добавлен в чёрный список",
        "text_for_alarm": "Пользователь добавлен в чёрный список",
        "text_for_user": "Вас добавили в чёрный список"
    }
}


@dp.callback_query_handler(callback_auth.filter(action=['auth_user', 'unauth_user']),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin())
async def auth_user(call: types.CallbackQuery, callback_data: dict):
    data = callback_data.get("data")
    telegram_id, email = data.split("_")
    action = callback_data.get("action")
    if action == "auth_user":
        user: User = User.get_user_by_email(email)
        wait_user: User = User.get_user_by_telegram_id(telegram_id)
        wait_user.remove_self()
        user.set_telegram_id(telegram_id)
        answer = f"{user.full_name()}, вы авторизовались с почтой: {user.get_email()}"

        await bot.send_message(user.telegram_id, answer)
        await call.message.edit_text(f"Пользователь {user.full_name()} добавлен в список: user")
        await call.answer(f"Пользователь {user.full_name()} теперь: user", show_alert=True)
        await call.answer()

    elif action == "unauth_user":
        user: User = User.get_user_by_telegram_id(telegram_id)
        user.change_status("blocked", "wait")
        try:
            await bot.send_message(user.telegram_id, f"Вас добавили в список: blocked")
        except aiogram.utils.exceptions.ChatNotFound:
            await bot.send_message(User.get_admin_id(),
                                   'Пользователь не получил уведомления, так как не имеет диалога с ботом')
            admin_logger.info("%s НЕ получил уведомление о смене статуса" % user.full_name())
        await call.message.edit_text(f"Пользователь {user.full_name()} добавлен в список: blocked")
        await call.answer(f"Пользователь {user.full_name()} теперь: blocked", show_alert=True)
        await call.answer()


@dp.callback_query_handler(callback_auth.filter(action=['add_user', 'block_user']),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin())
async def user_fate(call: types.CallbackQuery, callback_data: dict):
    fate = callback_data["action"].split("_")[0]
    user_id: int = int(callback_data["data"])
    user: User = User.get_user(user_id)
    if fate == "add":
        future_status = "user"
    else:
        future_status = "blocked"
    user.change_status(future_status, "wait")
    await call.answer(f"Пользователь {user.full_name()} теперь: {future_status}", show_alert=True)
    await call.answer()
    await call.message.edit_text(f"Пользователь {user.full_name()} добавлен в список: {future_status}")
    try:
        await bot.send_message(user.telegram_id, f"Вас добавили в список: {future_status}")
    except aiogram.utils.exceptions.ChatNotFound:
        await bot.send_message(User.get_admin_id(),
                               'Пользователь не получил уведомления, так как не имеет диалога с ботом')
        admin_logger.info("%s НЕ получил уведомление о смене статуса" % user.full_name())


@dp.callback_query_handler(callback_auth.filter(action=['known_user', 'blocked_user']),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin())
async def user_decide(call: types.CallbackQuery, callback_data: dict):
    case = callback_data['action']
    old_case = 'known_user' if case == 'blocked_user' else "blocked_user"
    user: User = User.get_user(int(callback_data['data']))
    admin_logger.info("%s выбрал %s для переноса в список %s" % (call.from_user.full_name, user.full_name(), case))
    user.change_status(LIST_ATTRIBUTES[case]["new_status"], LIST_ATTRIBUTES[old_case]["new_status"])
    await call.answer(LIST_ATTRIBUTES[case]["text_for_alarm"], show_alert=True)
    await call.answer()
    await call.message.edit_text(LIST_ATTRIBUTES[case]["text_for_admin"] % user.full_name())
    try:
        await bot.send_message(user.telegram_id, LIST_ATTRIBUTES[case]["text_for_user"])
        admin_logger.info("%s получил уведомление о смене статуса" % user.full_name())
    except aiogram.utils.exceptions.ChatNotFound:
        await bot.send_message(User.get_admin_id(),
                               'Пользователь не получил уведомления, так как не имеет диалога с ботом')
        admin_logger.info("%s НЕ получил уведомление о смене статуса" % user.full_name())


@dp.callback_query_handler(callback_auth.filter(action='cancel'),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin())
async def add_cancel(call: types.CallbackQuery, state: FSMContext):
    admin_logger.info("%s Жмёт отмену" % call.from_user.full_name)
    await call.message.edit_text('Выбор отменён.')
    await state.finish()
    await call.answer()


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin(),
                    commands="change_status")
async def status_changer(message: types.Message):
    admin_logger.info("%s запрашивает списки пользователей" % message.from_user.full_name)
    data_for_keyboard = [KeyboardData('Пользователи', 0, 'list_user'),
                         KeyboardData('Заблокированные', 0, 'list_blocked')]
    keyboard = get_keyboard_admin(data_for_keyboard)
    await message.answer('Выбери список для поиска пользователя, которому хочешь изменить статус',
                         reply_markup=keyboard)


@dp.callback_query_handler(callback_auth.filter(action=['list_user', 'list_blocked']),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin())
async def select_list(call: types.CallbackQuery, callback_data: dict):
    selected_list = callback_data['action'].split('_')[1]
    admin_logger.info("%s запрашивает список %s" % (call.from_user.full_name, selected_list))
    keyboard = get_keyboard_admin(get_users_of_list(selected_list), width=2)
    await call.message.edit_text('Выберите пользователя:', reply_markup=keyboard)


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin(), commands='news')
async def wait_for_news(message: types.Message):
    admin_logger.info("%s вводит новость" % message.from_user.full_name)
    await message.answer('Введите новость:')
    await OrderMenu.wait_news.set()
    return


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin(), state=OrderMenu.wait_news)
async def news_to_users(message: types.Message, state: FSMContext):
    admin_logger.info("%s отправил новость" % message.from_user.full_name)
    users: list[list[str, int]] = [[i.full_name(), i.telegram_id] for i in Status.get_users("user") if i.telegram_id]
    for name, telegram_id in users:
        news = message.text
        text = f'{name}, Это новости бота 🙃\n\n{news}'
        try:
            await bot.send_message(telegram_id, text)
            admin_logger.info("%s получил новость" % name)
        except aiogram.utils.exceptions.ChatNotFound:
            admin_logger.error("%s НЕ получил новость" % name)
        except aiogram.utils.exceptions.BotBlocked:
            admin_logger.error("%s заблокировал бота" % name)
    await state.finish()
    await message.answer('Отправлено')


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_admin(), commands='log')
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
