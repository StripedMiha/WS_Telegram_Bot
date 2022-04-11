import logging
from pprint import pprint
from typing import Union, Optional

import aiogram.types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.callback_data import CallbackData
from sqlalchemy.exc import NoResultFound

from app.KeyboardDataClass import KeyboardData
from app.create_log import setup_logger
from app.db.structure_of_db import User, Comment, Bookmark, Task, Project, Status
from app.tgbot.handlers.admin_handlers import get_keyboard_admin

back_logger: logging.Logger = setup_logger("App.back.user", "app/log/b_user.log")

# Словарь для считывания инлайн кнопок
callback_menu = CallbackData("fab_menu", "action")
callback_search = CallbackData("fab_search", "action", "path")
callback_remove = CallbackData("fab_remove", "action", "id")
callback_cancel = CallbackData("fab_cancel", "action", "purpose")

# Набор кнопок выбора даты
DATE_BUTTONS = ["Вчера", "Сегодня", "Отмена"]

# Набор кнопок выбора действия с задачей
TASK_BUTTONS = ["Выбрать по умолчанию", "Добавить закладку", "Ничего не понял", "Отмена"]

CANCEL_BUTTON = ["Отмена"]

TEXT_HELP = [
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


# Создание клавиатуры быстрого набора
def get_fast_keyboard(buttons: list, width: int = 3) -> ReplyKeyboardMarkup:
    fast_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=width)
    fast_keyboard.add(*buttons)
    return fast_keyboard


# Формирование инлайн клавиатуры меню
def get_keyboard(list_data: list[list], width: int = 3, enable_cancel: Union[bool, str] = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, action in list_data:
        buttons.append(InlineKeyboardButton(text=name,
                                            callback_data=callback_menu.new(action=action)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(
            text="Отмена",
            callback_data=callback_menu.new(
                action="cancel" if isinstance(enable_cancel, bool) else enable_cancel)
        ))
    keyboard = InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


async def get_user_help(telegram_id: int) -> Optional[str]:
    """
    По айди тилеграмма ищет пользователя. При наличии доступа возвращает помощь.
    При блокировании - игнорирует.
    :param telegram_id:
    :return:
    """
    try:
        user: User = User.get_user_by_telegram_id(telegram_id)
        if user.is_blocked():
            return None
        elif user.has_access():
            answer = '\n'.join(TEXT_HELP)
        else:
            answer = "Вы в листе ожидания авторизации. Ожидайте."
    except NoResultFound:
        answer = 'Нет доступа\nНапиши /start в личные сообщения боту, чтобы запросить доступ'
    return answer


async def validate_old_user(message: aiogram.types.Message):
    """
    Формирует и возвращает словарь данных для наполнения сообщений для валидации почты и пользователя
    :param message:
    :return:
    """
    to_admin_message: str
    to_user_message: str
    keyboard: InlineKeyboardMarkup
    email = message.text.strip(" ")
    if email in User.get_empty_email():
        un_auth_user: User = User.new_user(message.from_user.id,
                                           message.from_user.first_name,
                                           message.from_user.last_name)
        exist_user: User = User.get_user_by_email(email)
        data = "_".join([str(un_auth_user.telegram_id), email])
        data_for_keyboard = [KeyboardData('Добавить пользователя', data, 'auth_user'),
                             KeyboardData('Игнорировать пользователя', data, 'unauth_user')]
        keyboard = get_keyboard_admin(data_for_keyboard, width=1, enable_cancel=False)
        to_admin_message = f"Этот перец пишет мне: {un_auth_user.full_name()} " \
                           f"c id{un_auth_user.telegram_id} {message.from_user.username}\n" \
                           f"И утверждает, что он {exist_user.full_name()} и почта: {email} его"
        to_user_message = "Заявка ушла админу. Ждите."
        answer: dict = {
            "to_admin": to_admin_message,
            "to_user": to_user_message,
            "keyboard": keyboard,
            "to_log": f"{un_auth_user.full_name()} отправил запрос подтверждения, что он {exist_user.full_name()}",
            "finish": False
        }
    elif message.text.lower() == "отмена" or message.text.lower() == "cancel":
        answer: dict = {
            "to_user": "Отменён ввод почты.",
            "to_log": f"{message.from_user.full_name} отменил ввод почты для подтверждения",
            "finish": True
        }
    else:
        answer: dict = {
            "to_user": "Почта введена в неверном формате.\n"
                       "Введите 'Отмена' для отмены ввода",
            "to_log": f"{message.from_user.full_name} ввёл что-то некорректное: {message.text}",
            "finish": False
        }
    return answer
