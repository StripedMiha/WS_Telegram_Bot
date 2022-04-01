import logging
import re
from pprint import pprint

import aiogram.utils.exceptions

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup

from app.back.back_manager import get_manager_menu, get_managers_project, get_types_staff, get_users_list_by_type_staff, \
    change_user_status_in_project, finish_creating_project, get_manager_help, get_keyboard_of_settings, \
    archiving_project, get_report
from app.create_log import setup_logger
from app.tgbot.loader import dp, bot
from app.db.structure_of_db import User, Status, Project
from app.back.back_manager import callback_manager, callback_manager_select, callback_manager_decision

manager_logger: logging.Logger = setup_logger("App.Bot.manager", "app/log/h_manager.log")


class OrderCreateProject(StatesGroup):
    wait_for_project_name = State()
    wait_for_project_description = State()


@dp.callback_query_handler(callback_manager.filter(action="cancel"))
@dp.callback_query_handler(callback_manager_select.filter(action="cancel"))
@dp.callback_query_handler(callback_manager_decision.filter(action="cancel"))
async def manager_cancel(call: types.CallbackQuery):
    """
    Удаляет клавиатуру кнопок.
    :param call:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{user.full_name()} нажал кнопку отмены")
    await call.message.edit_text("Выбор отменён.")


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_manager(),
                    commands="help_manager")
async def manager_help(message: types.Message):
    """
        Выводит помощь для менеджера
        :param message:
        :return:
        """
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    manager_logger.info(f"{user.full_name()} ввёл команду /help_manager")
    await message.answer(await get_manager_help())


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_manager(),
                    commands="manager_menu")
async def manager_commands(message: types.Message) -> None:
    """
    По команде /manager выводит меню менеджерских команд
    :param message:
    :return: None
    """

    manager_logger.info(f"{User.get_user_by_telegram_id(message.from_user.id).full_name()} ввёл команду /manager_menu")
    await message.answer("Команды менеджера:", reply_markup=await get_manager_menu())


@dp.callback_query_handler(callback_manager.filter(action="add_to_project"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_manager())
async def select_project_for_staff(call: types.CallbackQuery):
    """
    По нажатию кнопки "Назначить на проект" выводит клавиатуру проектов данного менеджера
    :param call:
    :return:
    """
    user = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{user.full_name()} нажал кнопку 'Назначить на проект'")
    keyboard: InlineKeyboardMarkup = await get_managers_project(user, "staff")
    await call.message.edit_text("Выберите проект для которого хотите назначить или удалить исполнителей",
                                 reply_markup=keyboard)


@dp.callback_query_handler(callback_manager_select.filter(action="add_staff_on_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def list_types_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Вывод клавиатуры выбора отдела персонала который необходимо назначить на проект
    :param call:
    :param callback_data:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    manager_logger.info(f"{user.full_name()} выбрал проект ID{project.project_id} {project.project_name}")
    await call.message.edit_text("Выберите отдел сотрудников", reply_markup=await get_types_staff(user, project))


@dp.callback_query_handler(callback_manager_decision.filter(action=["get_constructor", "get_designer",
                                                                    "get_electronic", "get_manager", "get_graphics"]),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def users_list_by_type_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Вывод клавиатуры списка сотрудников для добавления в проект или исключения их из проекта.
    :param call:
    :param callback_data:
    :return:
    """
    selected_list: str = callback_data.get("action").split("_")[-1]
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    manager_logger.info(f"{manager.full_name()} выбрал список {selected_list} для выбора сотрудников в проекте"
                        f"ID{project.project_id} {project.project_name}")
    await call.message.edit_text(f"Выберите пользователя которого включить/исключить из {project.project_name}",
                                 reply_markup=await get_users_list_by_type_staff(project, selected_list))


@dp.callback_query_handler(callback_manager_decision.filter(action=["change_constructor", "change_designer",
                                                                    "change_electronic", "change_manager",
                                                                    "change_graphics"]))
async def change_user_in_project(call: types.CallbackQuery, callback_data: dict):
    """
    Меняет выбранному пользователю статус участия в проекте и обновляет клавиатуру с учётом изменений
    :param call:
    :param callback_data:
    :return:
    """
    selected_list: str = callback_data.get("action").split("_")[-1]

    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    user: User = User.get_user(int(callback_data.get("user_id")))
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    manager_logger.info(f"{manager.full_name()} меняет статус {user.full_name()} в проекте "
                        f"ID{project.project_id} {project.project_name}")
    try:
        text = await change_user_status_in_project(user, project)
        await bot.send_message(user.telegram_id, text)
    except aiogram.utils.exceptions.ChatNotFound:
        pass
    except aiogram.utils.exceptions.ChatIdIsEmpty:
        pass
    await call.message.edit_text(f"Выберите пользователя которого включить/исключить из {project.project_name}",
                                 reply_markup=await get_users_list_by_type_staff(project, selected_list))


@dp.callback_query_handler(callback_manager.filter(action="complete_adding"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def manager_cancel(call: types.CallbackQuery):
    """
    Завершает добавление пользователей. Аналогично отмене, но с иным текстом
    :param call:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{user.full_name()} нажал кнопку завершение ввода")
    await call.message.edit_text("Ввод завершён.")


@dp.callback_query_handler(callback_manager.filter(action="create_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def start_create_project(call: types.CallbackQuery):
    """
    Реакция на нажатие кнопки создания проекта. Запуск ожидания ввода названия проекта
    :param call:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{user.full_name()} начинает создание проекта")
    await call.message.edit_text("Введите название проекта с использованием шаблона 'abcd-001'")
    await OrderCreateProject.wait_for_project_name.set()


PROJECT_NAME_TEMPLATE = r"^[a-z,A-Z]{3,5}-\d{3}[a-z,-]?\d?\d?"


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager(),
                    state=OrderCreateProject.wait_for_project_name)
async def wait_project_name(message: types.Message, state: FSMContext):
    """
    Ожидание ввода корректного названия проекта. Или отмены создания проекта.
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    message_text: str = message.text
    manager_logger.info(f"{manager.full_name()} ввёл название {message_text}")
    if re.match(PROJECT_NAME_TEMPLATE, message_text):
        await state.update_data(project_name=message_text)
        await message.answer(f"Напишите описание проекта для {message_text}")
        await OrderCreateProject.wait_for_project_description.set()
    elif message_text.lower() == "cancel" or message_text.lower() == "отмена":
        await message.answer("Отмена создания проекта")
        await state.finish()
    else:
        await message.answer("Вы ввели некорректное название для проекта\n")


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager(),
                    state=OrderCreateProject.wait_for_project_description)
async def wait_project_description(message: types.Message, state: FSMContext):
    """
    Ожидание ввода описания проекта. Или отмены создания проекта.
    Создание проекта и вывод сообщения об успешном создании проекта.
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    message_text: str = message.text
    manager_logger.info(f"{manager.full_name()} ввёл описание {message_text}")
    if message_text.lower() == "cancel" or message_text.lower() == "отмена":
        await message.answer("Отмена ввода описания проекта и создания проекта")
        await state.finish()
        return
    data: dict = await state.get_data()
    project_name: str = data.get("project_name")
    await message.answer(await finish_creating_project(manager, project_name, message_text))
    await state.finish()


@dp.callback_query_handler(callback_manager.filter(action="manage_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def edit_project_menu(call: types.CallbackQuery, callback_data: dict):
    """
    Вывод клавиатуры проектов менеджера для редактирования
    :param call:
    :param callback_data:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{manager.full_name()} вызывает меню редактирования проекта")
    keyboard: InlineKeyboardMarkup = await get_managers_project(manager, "edit")
    await call.message.edit_text("Выберите проект для редактирования", reply_markup=keyboard)


@dp.callback_query_handler(callback_manager_select.filter(action="edit_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def select_setting(call: types.CallbackQuery, callback_data: dict):
    """
    Вывод клавиатуры редактирования проекта.
    :param call:
    :param callback_data:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project: Project = Project.get_project(callback_data.get("project_id"))
    manager_logger.info(f"{manager.full_name()} будет редактировать проект {project.project_name}")
    keyboard: InlineKeyboardMarkup = await get_keyboard_of_settings(project)
    await call.message.edit_text(f"Выберите что хотите отредактировать в проекте {project.project_name}",
                                 reply_markup=keyboard)


@dp.callback_query_handler(callback_manager_select.filter(action="archive_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def archiving_the_project(call: types.CallbackQuery, callback_data: dict):
    """
    Меняет проекту статус на "archive" и уведомляет об этом участников проекта.
    :param call:
    :param callback_data:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project: Project = Project.get_project(callback_data.get("project_id"))
    manager_logger.info(f"{manager.full_name()} архивирует проект {project.project_name}")
    text: str = await archiving_project(project)
    await call.message.edit_text(text)
    for user in [user for user in project.users if user != manager]:
        try:
            await bot.send_message(user.telegram_id, text)
        except (aiogram.utils.exceptions.ChatNotFound, aiogram.utils.exceptions.ChatIdIsEmpty):
            await bot.send_message(manager.telegram_id,
                                   f"{user.full_name()} не получил уведомление об архивации проекта")


@dp.callback_query_handler(callback_manager.filter(action="report_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def report(call: types.CallbackQuery):
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{manager.full_name()} получил ссылку на бота с отчётами")
    await call.message.edit_text(await get_report())


@dp.callback_query_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def sorry(call: types.CallbackQuery):
    pprint(call)
    await call.answer("Пока не работает, сорре", show_alert=True)
