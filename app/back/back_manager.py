import logging
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData

from app.back.user_back import get_number_max_page, get_next_prev_page_number
from app.create_log import setup_logger
from app.db.structure_of_db import User, Task, Project, Status

back_logger: logging.Logger = setup_logger("App.back.manager", "app/log/b_manager.log")

# Словарь для считывания инлайн кнопок
callback_manager = CallbackData("fab_menu", "action")
callback_manager_select = CallbackData("button_text", "action", "project_id")
callback_manager_decision = CallbackData("button_text", "action", "project_id", "user_id")


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
    for name, action, data_id in list_data:
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
    for name, action, project_id, user_id in list_data:
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
    Возвращает текст помощи для менеджера.
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
        ("Назначить на проект", "add_to_project", "0_1"),
        ("Редактировать проект", "manage_project", "0_1"),
        ("Отчёт по проекту", "report_project", "0_1"),
        ("Создать проект", "create_project", "0_1"),
        ("Информация о проекте", "project_list", "0_1"),
    ]
    return get_keyboard_1(buttons, 1)


TARGET_QUERY: dict = {"add_to_project": "add_staff_on_project",
                      "manage_project": "edit_project"}

BACK_QUERY: dict = {"add_to_project": "add_to_project",
                    "manage_project": "manage_project"}


async def get_project_pages_data_for_keyboard(max_page: int, page: int, hide_archive: int,
                                              action: str) -> Optional[list[tuple]]:
    """
    Получаем набор данных для кнопок перелистывания
    :param action:
    :param max_page: Номер последней страницы.
    :param page: Текущая страница.
    :param hide_archive: Статус отображения скрытых проектов.
    :return:
    """
    if max_page > page or (max_page == page and max_page > 0):
        prev_page, next_page = await get_next_prev_page_number(page, max_page)
        page_buttons: list[tuple] = [("⬅", action, f"{prev_page}_{hide_archive}"),
                                     ("➡", action, f"{next_page}_{hide_archive}")]
    else:
        page_buttons: None = None
    return page_buttons


async def get_status_button(hide_status: int, action: str) -> tuple:
    if hide_status:
        status_button: tuple = ("📦Показать архивные", action, f"0_0")
    else:
        status_button: tuple = ("📦Скрыть архивные", action, f"0_1")
    return status_button


async def get_managers_project(user: User, purpose: str,
                               data: str) -> (InlineKeyboardMarkup, str, str):
    """
    Возвращает менеджеру клавиатуру проектов, с указанным статусом,
    к которым у него есть доступ.action зашитый в кнопку определяется по ключу.
    :param user: Экземпляр менеджера.
    :param purpose: Цель запроса, по ключу определяется action, который будет зашит в кнопку.
    :param data: Данные текущей страницы и статус отображения неактивных проектов.
    :return: Экземпляр InlineKeyboardMarkup клавиатуры
    """
    page: int
    hide_status: int
    page, hide_status = [int(i) for i in data.split("_")]

    projects: list[Project] = [project for project in user.projects
                               if project.project_status == "active"]

    projects_button: list[tuple] = [(project.project_name,
                                     TARGET_QUERY.get(purpose),
                                     project.project_id)
                                    for project in projects]

    if not hide_status:
        archive_projects: list[Project] = [project for project in user.projects
                                           if project.project_status == "archive"]
        for one in archive_projects:
            projects_button.append(("📦 " + one.project_name, TARGET_QUERY.get(purpose), one.project_id))

    if len(projects_button) % 2 != 0:
        projects_button.append(("  ", "empty_button", "---"))

    button_on_page: int = 20
    max_page: int = await get_number_max_page(len(projects_button), button_on_page)

    log: str = f"{user.full_name()} запросил список проектов "
    text: str = ""

    # Получаем данные для кнопок перелистывания
    page_buttons: Optional[list[tuple]] = await get_project_pages_data_for_keyboard(max_page, page, hide_status,
                                                                                    purpose)

    if page_buttons is not None:
        text += f"Страница {page + 1}/{max_page + 1} "
        log += f"Страница {page + 1}/{max_page + 1} "

    split_projects: list[tuple] = projects_button[page * button_on_page: button_on_page + (page * button_on_page)]

    if page_buttons is not None:
        for but in page_buttons:
            split_projects.append(but)

    status_button: tuple = await get_status_button(hide_status, BACK_QUERY.get(purpose))
    split_projects.append(status_button)
    if status_button[-1].split("_")[-1] == '1':
        text += "включая архивные"
        log += "включая архивные"

    return get_keyboard_1(split_projects, width=2), text, log


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
                                                                                  project_id="0_1")))
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
    :param manager: экземпляр класса User которому будет добавлен созданный проект
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
        ("Изменить название", "change_project_name", project.project_id),  # TODO
        ("Изменить описание", "change_project_description", project.project_id),  # TODO
        ("Отправить в архив", "archive_project", project.project_id),
    ]
    keyboard: InlineKeyboardMarkup = get_keyboard_1(buttons, 1)
    return keyboard


async def archiving_project(project: Project) -> tuple[str, bool]:
    """
    Архивирование проекта и возврат сообщения менеджеру
    :param project:
    :return:
    """
    if project.project_status == "active":
        project.archive_project()
        answer: str = f"Проект '{project.project_name}' отправлен в архив."
        mailing_status: bool = True
    else:
        answer: str = f"Проект '{project.project_name}' итак в архиве."
        mailing_status: bool = False
    return answer, mailing_status


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
    buttons: List[tuple] = [("Активировать проект", "reactivate_project", task.project_id),
                            ("Оставить как есть", "keep_as_is", task.project_id)]
    keyboard: InlineKeyboardMarkup = get_keyboard_1(buttons, 2, False)
    return text, keyboard


async def get_report() -> str:
    """
    Возвращает сообщение со ссылкой на Telegram-бота с отчётами.
    :return:
    """
    text = f"Для формирования отчётов существует отдельный бот Даниила Затерюкина\n" \
           f"@SMDEmanage_bot вот он."
    return text
