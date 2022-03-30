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
callback_manager_select = CallbackData("button_text", "project_id", "action")
callback_manager_decision = CallbackData("button_text", "project_id", "user_id", "action")


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


# Формирование инлайн клавиатуры меню
def get_keyboard_1(list_data: list[tuple], width: int = 3, enable_cancel: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, data_id, action in list_data:
        buttons.append(InlineKeyboardButton(text=name,
                                            callback_data=callback_manager_select.new(action=action,
                                                                                      project_id=data_id)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="Отмена",
                                            callback_data=callback_manager_select.new(action="cancel",
                                                                                      project_id='---')))
    keyboard = InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


# Формирование инлайн клавиатуры меню
def get_keyboard_2(list_data: list[tuple], width: int = 3, enable_cancel: bool = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, project_id, user_id, action in list_data:
        buttons.append(InlineKeyboardButton(text=name,
                                            callback_data=callback_manager_decision.new(action=action,
                                                                                        project_id=project_id,
                                                                                        user_id=user_id)))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="Отмена",
                                            callback_data=callback_manager_decision.new(action="cancel",
                                                                                        project_id='---',
                                                                                        user_id='---')))
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
        ("Информация о проекте", "project_list")
    ]
    return get_keyboard(buttons, 1)


TARGET_QUERY: dict = {"staff": "add_staff_on_project",
                      "edit": "edit_project"}


async def get_managers_project(user: User, purpose: str, project_status: str = "active") -> InlineKeyboardMarkup:
    """
    Возвращает менеджеру клавиатуру проектов, с указанным статусом :param project_status:, к которым у него есть доступ.
    action зашитый в кнопку определяется :param purpose: по ключу.
    :param user: экземпляр менеджера
    :param purpose: Цель запроса, по ключу определяется action, который будет зашит в кнопку.
    :param project_status: значение по которому будет фильтроваться статус проектов.
    :return: Экземпляр InlineKeyboardMarkup клавиатуры
    """
    projects: list[Project] = [project for project in user.projects if project.project_status == project_status]
    for_keyboard: list[tuple] = [(project.project_name, project.project_id, TARGET_QUERY.get(purpose)) for project in projects]
    return get_keyboard_1(for_keyboard, width=2)


async def get_types_staff(user: User, project: Project) -> InlineKeyboardMarkup:
    """
    Возвращает менеджеру клавиатуру списка отделов для выбора
    :param user:
    :param project:
    :return:
    """
    type_staff: list[tuple[str, str]] = [("Конструктор", "get_constructor"), ("Дизайнер", "get_designer"),
                                         ("Электронщик", "get_electronic"), ("Менеджер", "get_manager"),
                                         ("Saint", "get_graphics")]
    buttons: list[InlineKeyboardButton] = []
    for ru, action in type_staff:
        buttons.append(InlineKeyboardButton(text=ru,
                                            callback_data=callback_manager_decision.new(action=action,
                                                                                        project_id=project.project_id,
                                                                                        user_id=user.user_id)))
    buttons.append(InlineKeyboardButton(text="Вернутся к выбору проекта",
                                        callback_data=callback_manager.new(action="add_to_project")))
    buttons.append(InlineKeyboardButton(text="Отмена",
                                        callback_data=callback_manager.new(action="cancel")))
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    return keyboard


async def get_users_list_by_type_staff(project: Project, type_staff: str) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру пользователей по нажатию на кнопки которой будет меняться их статус участия в проекте.
    :param project:
    :param type_staff:
    :return:
    """
    selected_users: list[User] = [user for user in Status.get_users(type_staff)
                                  if Status.get_status("user") in user.statuses]
    selected_users.sort(key=lambda i: i.last_name)
    buttons: list[InlineKeyboardButton] = []
    for user in selected_users:
        bell = "🔔" if user.telegram_id else "🔕"
        if user in project.users:
            text = f"✅ {user.full_name()} {bell}"
        else:
            text = f"❌ {user.full_name()} {bell}"
        buttons.append(InlineKeyboardButton(text=text,
                                            callback_data=callback_manager_decision.new(action=f"change_{type_staff}",
                                                                                        project_id=project.project_id,
                                                                                        user_id=user.user_id)))
    buttons.append(InlineKeyboardButton(text="Вернутся к выбору отдела",
                                        callback_data=callback_manager_select.new(action="add_staff_on_project",
                                                                                  project_id=project.project_id)))
    buttons.append(InlineKeyboardButton(text="Завершить добавление",
                                        callback_data=callback_manager.new(action="complete_adding")))
    keyboard: InlineKeyboardMarkup = InlineKeyboardMarkup(row_width=1)
    keyboard.add(*buttons)
    return keyboard


async def change_user_status_in_project(user: User, project: Project) -> str:
    """
    Меняет статус участия пользователя в проекте.
    :param user:
    :param project:
    :return:
    """
    if project in user.projects:
        user.remove_project(project)
        text: str = f"Вы больше не состоите в проекте {project.project_name}"
    else:
        user.add_project(project)
        text: str = f"Вас добавили в проект {project.project_name}"
    return text


async def finish_creating_project(manager: User, project_name: str, project_description: str):
    new_project = Project.new_project(project_name, project_description)
    manager.add_project(new_project)
    return new_project
