import logging
from pprint import pprint
from typing import Union

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy.exc import NoResultFound

from app.create_log import setup_logger
from app.db.structure_of_db import User, Comment, Bookmark, Task, Project, Status

top_logger: logging.Logger = setup_logger("App.back.top", "app/log/b_top.log")

# Словарь для считывания инлайн кнопок
callback_top = CallbackData("fab_menu", "action")
callback_top_select = CallbackData("button_text", "user_id", "action")


# Формирование инлайн клавиатуры меню
def get_keyboard(list_data: list[tuple], width: int = 3, enable_cancel: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, action in list_data:
        buttons.append(InlineKeyboardButton(text=name, callback_data=callback_top.new(action=action)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="Отмена", callback_data=callback_top.new(action="cancel")))
    keyboard = InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# Формирование инлайн клавиатуры меню
def get_keyboard_1(list_data: list[tuple], width: int = 3, enable_cancel: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, data_id, action in list_data:
        buttons.append(InlineKeyboardButton(text=name,
                                            callback_data=callback_top_select.new(action=action,
                                                                                  user_id=data_id)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="Отмена",
                                            callback_data=callback_top_select.new(action="cancel",
                                                                                  user_id='---')))
    keyboard = InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


async def get_top_help() -> str:
    """
    Возвращает текст помощи для управление сотрудниками
    :return:
    """
    text = [f"/top_menu - выводит меню возможностей управления",
            f"<b>Список кнопок:</b>"]
    return "\n".join(text)


async def get_top_menu() -> InlineKeyboardMarkup:
    """
    Возвращает меню управленческих команд.
    :return: InlineKeyboardMarkup
    """
    buttons = [
        ("Назначить пользователя", "set_user"),
        ("Разжаловать пользователя", "remove_position")
        # ("Редактировать проект", "manage_project"),
        # ("Создать проект", "create_project"),
        # ("Информация о проекте", "project_list")
    ]
    return get_keyboard(buttons, 1)


async def get_select_staff(action: str) -> InlineKeyboardMarkup:
    """
    Возвращает меню выбора в какой отдел назначить.
    :return: InlineKeyboardMarkup
    """
    keyboard_dict: dict = {
        'add': [
            ("Назначить менеджера", "set_manager"),
            ("Назначить дизайнера", "set_designer"),
            ("Назначить конструктора", "set_constructor"),
            ("Назначить в Saint", "set_graphics"),
            ("Назначить электронщика", "set_electronic"),
            ("Назначить управление персоналом", "set_topmanager")
        ],
        "remove": [
            ("Разжаловать менеджера", "remove_manager"),
            ("Разжаловать дизайнера", "remove_designer"),
            ("Разжаловать конструктора", "remove_constructor"),
            ("Разжаловать в Saint", "remove_graphics"),
            ("Разжаловать электронщика", "remove_electronic"),
            ("Разжаловать управление персоналом", "remove_topmanager")
        ]}

    return get_keyboard(keyboard_dict[action], 1)


async def get_ru_type_staff(eng_word: str) -> str:
    """
    Возвращает переведённое на русский название позиции сотрудника
    :param eng_word:
    :return:
    """
    eng_ru_dict: dict = {
        "manager": "менеджер",
        "designer": "дизайнер",
        "constructor": "конструктор",
        "graphics": "сэйнтист",
        "electronic": "электронщик",
        "topmanager": "управляющий",
    }
    return eng_ru_dict[eng_word]


async def get_possible_user(selected_position: str) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру пользователей для добавления их в выбранный отдел
    :param selected_position:
    :return:
    """
    not_position: Status = Status.get_status(selected_position)
    user_status: Status = Status.get_status("user")
    users: list[User] = [user for user in User.get_all_users()
                         if user_status in user.statuses and not_position not in user.statuses]
    return get_keyboard_1([(user.full_name(), user.user_id, f"set_{selected_position}") for user in users], 1)


async def add_user_in_department(user: User, selected_department: str) -> str:
    """
    Добавляет выбранному пользователю user новую должность
    :param user:
    :param selected_department:
    :return:
    """
    user.add_status(selected_department)
    return f"{user.full_name()} поставлен на позицию"


async def get_selected_staff_user(selected_position: str) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру пользователей для добавления их в выбранный отдел
    :param selected_position:
    :return:
    """
    selected_list_position: Status = Status.get_status(selected_position)
    user_status: Status = Status.get_status("user")
    users: list[User] = [user for user in User.get_all_users()
                         if user_status in user.statuses and selected_list_position in user.statuses]
    return get_keyboard_1([(user.full_name(), user.user_id, f"remove_{selected_position}") for user in users], 1)


async def remove_user_from_department(user: User, selected_department: str) -> str:
    """
    Добавляет выбранному пользователю user новую должность
    :param user:
    :param selected_department:
    :return:
    """
    user.remove_status(selected_department)
    return f"{user.full_name()} удалён с позиции"
