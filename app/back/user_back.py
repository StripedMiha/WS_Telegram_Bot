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
callback_search = CallbackData("fab_search", "action", "id")
callback_search_pages = CallbackData("fab_page", "action", "page", "hide")
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

INPUT_COSTS = """
Введите часы и описание деятельности:
Можно ввести в одну строку, можно в несколько(но в одном сообщении).
В начале указываете количество часов, следом через '!' можно перечислить один или несколько комментариев.
Можно ввести больше двух часов. Алгоритм сам разделит по два часа. Пробелы между '!' не важны

Шаблон: 
{число часов}!{описание деятельности}!{описание деятельности}
Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> ! <i>Сборка печатного прототипа</i>

Для создания подзадачи введите 'создать подзадачу'.
Для закрытия задачи введите 'задача выполнена'.
"""


# Создание клавиатуры быстрого набора
def get_fast_keyboard(buttons: list, width: int = 3) -> ReplyKeyboardMarkup:
    fast_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=width)
    fast_keyboard.add(*buttons)
    return fast_keyboard


# Формирование инлайн клавиатуры меню
async def get_keyboard(list_data: list[list], width: int = 3,
                       enable_cancel: Union[bool, str] = True) -> InlineKeyboardMarkup:
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


# Формирование инлайн клавиатуры меню
async def get_search_keyboard(list_data: list[tuple],
                              page_buttons: Optional[list[tuple]] = None,
                              status_button: Optional[tuple] = None,
                              width: int = 3,
                              enable_cancel: Union[bool, str] = True) -> InlineKeyboardMarkup:
    buttons = []
    for name, action, id in list_data:
        buttons.append(InlineKeyboardButton(text=name,
                                            callback_data=callback_search.new(action=action,
                                                                              id=id)))

    if status_button is not None:
        buttons.append(InlineKeyboardButton(text=status_button[0],
                                            callback_data=callback_search_pages.new(action=status_button[1],
                                                                                    page=status_button[2],
                                                                                    hide=status_button[3])))
    if enable_cancel:
        buttons.append(InlineKeyboardButton(text="❌ Отмена", callback_data=callback_menu.new(action="cancel")))
    if page_buttons:
        for text, action, page, status_hide in page_buttons:
            buttons.append(InlineKeyboardButton(text=text,
                                                callback_data=callback_search_pages.new(action=action,
                                                                                        page=page,
                                                                                        hide=status_hide)))
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


async def get_type_of_search_keyboard() -> InlineKeyboardMarkup:
    buttons = [('Через поиск', 'via_search'),
               ('❤ Через закладки', 'via bookmarks'),
               ('Задача по умолчанию', 'fast input')]
    return await get_keyboard(buttons, width=2)


async def get_number_max_page(count: int, max_on_page: int = 10) -> int:
    if count <= max_on_page:
        return 0
    else:
        if count % max_on_page == 0:
            return (count // max_on_page) - 1
        else:
            return count // max_on_page


async def get_project_list(user: User,
                           page: int = 0,
                           hide_archive: bool = True) -> tuple[str, InlineKeyboardMarkup, str]:
    """
    Возвращает набор данных для клавиатуры выбора проекта
    :param page:
    :param user:
    :param hide_archive: показывать ли архивные проекты
    :return:
    """
    projects: list[tuple] = [(i.project_name, "search_task", i.project_id) for i in user.projects
                             if i.project_status == "active"]
    projects.sort(key=lambda project: project[0])
    if not hide_archive:
        archive_projects: list[tuple] = [("📦 " + i.project_name, "search_task", i.project_id)
                                         for i in user.projects if i.project_status == "archive"]
        archive_projects.sort(key=lambda project: project[0])
        for archive_project in archive_projects:
            projects.append(archive_project)
    button_on_page: int = 20
    if len(projects) % 2 != 0:
        projects.append(("  ", "empty_button", "---"))
    max_page: int = await get_number_max_page(len(projects), button_on_page)
    log: str = f"{user.full_name()} запросил список проектов"
    text: str = "Выберите проект:"
    if max_page > page or (max_page == page and max_page > 0):
        next_page, prev_page = page + 1, page - 1
        if next_page > max_page:
            next_page = 0
        if prev_page < 0:
            prev_page = max_page
        page_buttons: list[tuple] = [("⬅ ", "via_search", prev_page, int(hide_archive)),
                                     ("➡ ", "via_search", next_page, int(hide_archive))]
        text += f" Страница {page + 1}/{max_page + 1}"
        log += text
    else:
        page_buttons: None = None

    split_projects: list[tuple] = projects[page * button_on_page: button_on_page + (page * button_on_page)]
    if hide_archive:
        status_button: tuple = ("📦Показать архивные", "via_search", 0, 0)
    else:
        status_button: tuple = ("Скрыть архивные", "via_search", 0, 1)
        text += "\t включая архивные"
        log += text
    keyboard: InlineKeyboardMarkup = await get_search_keyboard(split_projects,
                                                               page_buttons,
                                                               status_button,
                                                               width=2,
                                                               enable_cancel=True)
    return text, keyboard, log


def get_text_add_costs(task_id: int, user: User) -> str:
    task = Task.get_task(task_id)
    date = f'Установленная дата - {user.get_date(True)}'
    answer: str = '\n'.join([task.full_name(), date, INPUT_COSTS])
    return answer


async def get_tasks(parent_id: int,
                    user_id: int,
                    page: int = 0,
                    hide_done: bool = True,
                    sub: int = 0,) -> Union[tuple[str, InlineKeyboardMarkup, str], str]:
    """
    Возвращает набор данных для клавиатуры выбора задачи
    :param sub:
    :param page:
    :param parent_id: Если sub = True, то parent_id - parent_task_id, иначе - project_id
    :param user_id:
    :param hide_done: показывать ли закрытые задачи
    :return:
    """

    user: User = User.get_user_by_telegram_id(user_id)
    if not sub:
        tasks: list[Task] = Task.get_tasks(parent_id)
    else:
        tasks: list[Task] = Task.get_subtasks(parent_id)
    if len(tasks) == 0:
        return get_text_add_costs(parent_id, user)

    child_tasks: list[tuple] = []
    child_tasks += [(task.task_name, "search_subtask", task.task_id)
                    for task in tasks if task.status == "active"]
    if not hide_done:
        child_tasks += [("✅ " + task.task_name if task.status == "done" else task.task_name,
                         "search_subtask",
                         task.task_id)
                        for task in tasks if task.status == "done"]

    button_on_page: int = 20

    max_page: int = await get_number_max_page(len(child_tasks), button_on_page)
    log: str = f"{user.full_name()} запросил список задач"
    text: str = "Выберите задачу:"
    action: str = "subtask" if sub else "task"
    if max_page > page or (max_page == page and max_page > 0):
        next_page, prev_page = page + 1, page - 1
        if next_page > max_page:
            next_page = 0
        if prev_page < 0:
            prev_page = max_page
        page_buttons: list[tuple] = [("⬅ ", f"search_{action}", parent_id, f"{prev_page}_{int(hide_done)}_{sub}"),
                                     ("➡ ", f"search_{action}", parent_id, f"{next_page}_{int(hide_done)}_{sub}")]
        text += f" Страница {page + 1}/{max_page + 1}"
        log += text
    else:
        page_buttons: None = None

    split_tasks: list[tuple] = child_tasks[page * button_on_page: button_on_page + (page * button_on_page)]
    if len(split_tasks) % 2 == 0:
        split_tasks.append(("  ", "empty_button", "---"))
    split_tasks.append(("🛠Создать задачу", f"create_{action}", parent_id))

    if hide_done:
        status_button: tuple = ("✅показать выполненные", f"search_{action}", parent_id, f"0_0_{sub}")
    else:
        status_button: tuple = ("❌скрыть выполненные", f"search_{action}", parent_id, f"0_1_{sub}")
        text += "\t включая выполненные"
        log += text
    keyboard: InlineKeyboardMarkup = await get_search_keyboard(split_tasks,
                                                               page_buttons,
                                                               status_button,
                                                               width=2,
                                                               enable_cancel=True)
    return text, keyboard, log
