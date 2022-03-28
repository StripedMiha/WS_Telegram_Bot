import logging
import re
from datetime import datetime, timedelta
from pprint import pprint
from typing import Union

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy.exc import NoResultFound

from app.KeyboardDataClass import KeyboardData
from app.api.work_calendar import is_work_day
from app.create_log import setup_logger
from app.db.structure_of_db import User, Comment, Bookmark, Task, Project, Status


back_logger: logging.Logger = setup_logger("App.back.manager", "app/log/b_manager.log")


# Словарь для считывания инлайн кнопок
callback_manager = CallbackData("fab_menu", "action")


# Формирование инлайн клавиатуры меню
def get_keyboard(list_data: list[tuple], width: int = 3, enable_cancel: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, action in list_data:
        buttons.append(InlineKeyboardButton(text=name, callback_data=callback_manager.new(action=action)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="Отмена", callback_data=callback_manager.new(action="cancel")))
    keyboard = InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


async def get_manager_menu() -> InlineKeyboardMarkup:
    """
    Возвращает меню менеджерских команд
    :return: InlineKeyboardMarkup
    """
    buttons = [
        ("Назначить на проект", "add_to_project"),
        ("Редактировать проект", "manage_project"),
        ("Создать проект", "create_project"),
        ("Список ваших проектов", "project_list")
    ]
    return get_keyboard(buttons, 1)
