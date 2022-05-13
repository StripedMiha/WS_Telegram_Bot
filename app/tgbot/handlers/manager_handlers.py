import logging
import re
from pprint import pprint
from typing import List

from aiogram import types
from aiogram.utils.exceptions import ChatNotFound, BotBlocked, ChatIdIsEmpty, MessageIsTooLong
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup

from app.back.back_manager import get_manager_menu, get_managers_project, get_types_staff, get_users_list_by_type_staff, \
    change_user_status_in_project, finish_creating_project, get_manager_help, get_keyboard_of_settings, \
    archiving_project, get_report, change_project_description, PROJECT_NAME_TEMPLATE, change_project_name
from app.create_log import setup_logger
from app.tgbot.loader import dp, bot
from app.db.structure_of_db import User, Status, Project
from app.back.back_manager import callback_manager, callback_manager_select, callback_manager_decision

manager_logger: logging.Logger = setup_logger("App.Bot.manager", "app/log/h_manager.log")


class OrderCreateProject(StatesGroup):
    wait_for_project_name = State()
    wait_for_project_description = State()
    wait_for_new_project_name = State()
    wait_for_new_project_description = State()


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


@dp.callback_query_handler(callback_manager_select.filter(action="add_to_project"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_manager())
async def select_project_for_staff(call: types.CallbackQuery, callback_data: dict):
    """
    По нажатию кнопки "Назначить на проект" выводит клавиатуру проектов данного менеджера
    :param call:
    :return:
    """
    user = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{user.full_name()} нажал кнопку 'Назначить на проект'")
    statuses: str = callback_data.get("project_id")
    keyboard: InlineKeyboardMarkup
    text: str
    keyboard, text, log = await get_managers_project(user, "add_to_project", statuses)
    await call.message.edit_text(f"Выберите проект для которого хотите назначить или удалить исполнителей: \n{text}",
                                 reply_markup=keyboard)
    manager_logger.info(log)


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
    except (ChatNotFound, ChatIdIsEmpty):
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


@dp.callback_query_handler(callback_manager_select.filter(action="create_project"),
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
        manager_logger.info(f"Ввёл корректное название")
        await OrderCreateProject.wait_for_project_description.set()
    elif message_text.lower() == "cancel" or message_text.lower() == "отмена":
        await message.answer("Отмена создания проекта")
        manager_logger.info(f"Отмена создание проекта")
        await state.finish()
    else:
        manager_logger.info(f"Ввёл некорректное название")
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
        manager_logger.info(f"Отмена создания проекта")
        await state.finish()
        return
    data: dict = await state.get_data()
    project_name: str = data.get("project_name")
    await message.answer(await finish_creating_project(manager, project_name, message_text))
    await state.finish()


@dp.callback_query_handler(callback_manager_select.filter(action="manage_project"),
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
    statuses: str = callback_data.get("project_id")
    ans = await get_managers_project(manager, "manage_project", statuses)
    keyboard, text, log = ans
    await call.message.edit_text(f"Выберите проект для редактирования\n{text}", reply_markup=keyboard)
    manager_logger.info("Для редактирования " + log)


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
    text, mailing_status = await archiving_project(project)
    await call.message.edit_text(text)
    if mailing_status:
        for user in [user for user in project.users if user != manager]:
            try:
                await bot.send_message(user.telegram_id, text)
            except (ChatNotFound, ChatIdIsEmpty):
                await bot.send_message(manager.telegram_id,
                                       f"{user.full_name()} не получил уведомление об архивации проекта")


@dp.callback_query_handler(callback_manager_select.filter(action=["reactivate_project", "keep_as_is"]),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def handler_reactivate_project(call: types.CallbackQuery, callback_data: dict):
    """
    Обработчик кнопок выбора активации неактивного проекта
    :param call:
    :param callback_data:
    :return:
    """
    action: str = callback_data.get("action")
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    if action == "reactivate_project":
        project.activate_project()
        manager_logger.info(f"{manager.full_name()} активировал архивный проект {project.project_name}")
        await call.message.edit_text(f"Вы успешно активировали {project.project_name}")
        for user in [user for user in project.users if user.telegram_id and user.telegram_id != manager.telegram_id]:
            try:
                await bot.send_message(user.telegram_id,
                                       f"{manager.full_name()} вновь активировал проект {project.project_name}")
                manager_logger.info(f"{manager.full_name()} получил уведомление о реактивации проекта")
            except (ChatNotFound, BotBlocked, ChatIdIsEmpty) as err:
                manager_logger.error(
                    f"{manager.full_name()} не получил уведомление о реактивации проекта потому что {err}")
    else:
        manager_logger.info(f"{manager.full_name()} не стал менять статус у проекта {project.project_name}")


@dp.callback_query_handler(callback_manager_select.filter(action="change_project_description"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def handler_change_project_description(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """
    Обработчик начала изменения описания проекта и запуск ожидания ввода нового описания.
    :param call:
    :param callback_data:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    await state.update_data(project_id=project_id)
    await call.message.edit_text(f"Вы выбрали проект '{project.project_name}' для редактирования его описания\n"
                                 f"Текущее его описание вы можете скопировать с сообщения ниже.")
    manager_logger.info(
        f"{manager.full_name()} выбрали проект '{project.project_name}' для редактирования его описания")
    await call.message.answer(f"{project.project_description if project.project_description else 'Нет описания.'}")
    await OrderCreateProject.wait_for_new_project_description.set()


@dp.message_handler(lambda message: message.text.lower() in ["cancel", "отмена"],
                    state=OrderCreateProject.wait_for_new_project_description)
async def cancel_edit_project_description(message: types.Message, state: FSMContext):
    """
    Обработчик отмены редактирования описания проекта.
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    data = await state.get_data()
    project: Project = Project.get_project(int(data.get("project_id")))
    manager_logger.info(f"{manager.full_name()} отменил редактирование описания проекта с ID{project.project_id}")
    await message.answer("Отмена редактирования описания проекта.")
    await state.finish()


@dp.message_handler(state=OrderCreateProject.wait_for_new_project_description)
async def handler_edit_project_description(message: types.Message, state: FSMContext):
    """
    Обработчик ввода нового описания проекта
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    data: dict = await state.get_data()
    project: Project = Project.get_project(int(data.get("project_id")))
    new_description: str = message.text.strip(" ")
    to_other, to_manager = await change_project_description(manager, project, new_description)
    try:
        await message.answer(to_manager)
    except MessageIsTooLong:
        await message.answer("Новое описание было применено, но оно слишком длинное для вывода в сообщении.")
    for user in [user for user in project.users if user != manager]:
        try:
            await bot.send_message(user.telegram_id, to_other)
            manager_logger.info(to_other)
        except MessageIsTooLong:
            await bot.send_message(user.telegram_id,
                                   f"{manager.full_name()} ввёл настолько длинное новое описание проекта "
                                   f"'{project.project_name}', что я затрудняюсь его вывести в сообщении")
        except (ChatNotFound, BotBlocked, ChatIdIsEmpty) as err:
            manager_logger.error(
                f"{manager.full_name()} не получил уведомление об изменении описания проекта потому что {err}")
    await state.finish()


@dp.callback_query_handler(callback_manager_select.filter(action="change_project_name"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def handler_change_project_name(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """
    Обработчик начала изменения названия проекта и запуск ожидания ввода нового названия.
    :param call:
    :param callback_data:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    project_id: int = int(callback_data.get("project_id"))
    project: Project = Project.get_project(project_id)
    await state.update_data(project_id=project_id)
    await call.message.edit_text(f"Вы выбрали проект '{project.project_name}' для переименования\n")
    manager_logger.info(f"{manager.full_name()} выбрали проект '{project.project_name}' для переименования")
    await OrderCreateProject.wait_for_new_project_name.set()


@dp.message_handler(lambda message: message.text.lower() in ["cancel", "отмена"],
                    state=OrderCreateProject.wait_for_new_project_name)
async def cancel_edit_project_description(message: types.Message, state: FSMContext):
    """
    Обработчик отмены переименования проекта.
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    data = await state.get_data()
    project: Project = Project.get_project(int(data.get("project_id")))
    manager_logger.info(f"{manager.full_name()} отменил переименования проекта с ID{project.project_id}")
    await message.answer("Отмена переименования проекта.")
    await state.finish()


@dp.message_handler(lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager(),
                    state=OrderCreateProject.wait_for_new_project_name)
async def handler_edit_project_name(message: types.Message, state: FSMContext):
    """
    Ожидание ввода корректного названия проекта.
    :param message:
    :param state:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(message.from_user.id)
    message_text: str = message.text
    manager_logger.info(f"{manager.full_name()} ввёл название {message_text}")
    data = await state.get_data()
    project: Project = Project.get_project(data.get("project_id"))
    status, to_other, to_manager = await change_project_name(manager, project, message_text)
    await message.answer(to_manager)
    manager_logger.info(to_other)
    if status:
        for user in [user for user in project.users if user != manager]:
            try:
                await bot.send_message(user.telegram_id, to_other)
            except (ChatNotFound, BotBlocked, ChatIdIsEmpty) as err:
                manager_logger.error(
                    f"{manager.full_name()} не получил уведомление о переименовании проекта потому что {err}")
        await state.finish()


@dp.callback_query_handler(callback_manager_select.filter(action="report_project"),
                           lambda call: User.get_user_by_telegram_id(call.from_user.id).is_manager())
async def report(call: types.CallbackQuery):
    """
    Выводит сообщение со ссылкой на бота с отчётами.
    :param call:
    :return:
    """
    manager: User = User.get_user_by_telegram_id(call.from_user.id)
    manager_logger.info(f"{manager.full_name()} получил ссылку на бота с отчётами")
    await call.message.edit_text(await get_report())



