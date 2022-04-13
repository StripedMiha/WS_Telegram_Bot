import logging
from pprint import pprint
from typing import Union, List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy.exc import NoResultFound

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


async def get_manager_help() -> str:
    """
    Возвращает текст помощи для менеджера
    :return:
    """
    text = [f"/manager_menu - выводит меню возможностей менеджера",
            f"<b>Список кнопок:</b>"]
    return "\n".join(text)


async def get_manager_menu() -> InlineKeyboardMarkup:
    """
    Возвращает меню менеджерских команд
    :return: InlineKeyboardMarkup
    """
    buttons = [
        ("Назначить на проект", "active", "add_to_project"),
        ("Редактировать проект", "active", "manage_project"),
        ("Отчёт по проекту", "active", "report_project"),
        ("Создать проект", "active", "create_project"),
        ("Информация о проекте", "active", "project_list")
    ]
    return get_keyboard_1(buttons, 1)


TARGET_QUERY: dict = {"staff": "add_staff_on_project",
                      "edit": "edit_project"}

BACK_QUERY: dict = {"staff": "add_to_project",
                    "edit": "manage_project"}


async def get_managers_project(user: User, purpose: str,
                               project_statuses: List[str] = "active") -> InlineKeyboardMarkup:
    """
    Возвращает менеджеру клавиатуру проектов, с указанным статусом :param project_statuses:,
    к которым у него есть доступ.action зашитый в кнопку определяется :param purpose: по ключу.
    :param user: экземпляр менеджера.
    :param purpose: Цель запроса, по ключу определяется action, который будет зашит в кнопку.
    :param project_statuses: значение по которому будет фильтроваться статус проектов.
    :return: Экземпляр InlineKeyboardMarkup клавиатуры
    """
    projects: list[Project] = [project for project in user.projects if project.project_status in project_statuses]
    for_keyboard: list[tuple] = [
        ("📦 " + project.project_name if "archive" in project.project_status else project.project_name,
         project.project_id,
         TARGET_QUERY.get(purpose)
         )
        for project in projects]
    if "archive" in project_statuses:
        for_keyboard.append(("📦Скрыть архивные", "active", BACK_QUERY.get(purpose)))
    else:
        for_keyboard.append(("📦Показать архивные", "active_archive", BACK_QUERY.get(purpose)))
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
    buttons.append(InlineKeyboardButton(text="↩ Вернутся к выбору проекта",
                                        callback_data=callback_manager_select.new(action="add_to_project",
                                                                                  project_id="active")))
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
    buttons.append(InlineKeyboardButton(text="↩ Вернутся к выбору отдела",
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


async def finish_creating_project(manager: User, project_name: str, project_description: str) -> str:
    """
    Создаёт новый проект. Возвращает текстовое сообщение о создании нового проекта
    :param manager: экземпляр класса User которому будет добавлен свежесозданный проект
    :param project_name: имя нового проекта
    :param project_description: описание нового проекта
    :return:
    """
    new_project: Project = Project.new_project(project_name, project_description)
    manager.add_project(new_project)
    text = f"Вы создали новый проект.\n" \
           f"Имя проекта: {new_project.project_name}\n" \
           f"Описание проекта: {new_project.project_description}" \
           f"Проект доступен для управления."
    return text


async def get_keyboard_of_settings(project: Project) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру изменения проекта
    :param project: экземпляр класса Projects
    :return:
    """
    buttons = [
        ("Изменить название", project.project_id, "change_project_name"),  # TODO
        ("Изменить описание", project.project_id, "change_project_description"),  # TODO
        ("Отправить в архив", project.project_id, "archive_project"),
    ]
    keyboard: InlineKeyboardMarkup = get_keyboard_1(buttons, 1)
    return keyboard


async def archiving_project(project: Project) -> str:
    """
    Архивирование проекта и возврат сообщения менеджеру
    :param project:
    :return:
    """
    if project.project_status == "active":
        project.archive_project()
        answer: str = f"Проект {project.project_name} отправлен в архив."
    else:
        answer: str = f"Проект {project.project_name} итак в архиве."
    return answer


async def reactivate_project_keyboard(user: User, task: Task) -> tuple[str, InlineKeyboardMarkup]:
    """
    Возвращает набор данных для реактивации проекта
    :param user:
    :param task:
    :return:
    """
    text: str = f"{user.full_name()} внёс трудочасы в задачу {task.task_name} архивного проекта " \
                f"{task.project.project_name}. \n" \
                f"Активируем проект, чтобы было проще его находить и вносить часы в дальнейшем?"
    buttons: List[tuple] = [("Активировать проект", task.project_id, "reactivate_project"),
                            ("Оставить как есть", task.project_id, "keep_as_is")]
    keyboard: InlineKeyboardMarkup = get_keyboard_1(buttons, 2, False)
    return text, keyboard


async def get_report() -> str:
    """
    Возвращает сообщение со ссылкой на бота с отчётами.
    :return:
    """
    text = f"Для формирования отчтётов существует отдельный бот Даниила Затерюкина\n" \
           f"@SMDEmanage_bot вот он."
    return text
