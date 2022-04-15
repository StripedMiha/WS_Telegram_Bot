import logging

from aiogram import types


from app.back.top_back import get_top_help, callback_top, get_top_menu, get_select_staff, get_ru_type_staff, \
    get_possible_user, callback_top_select, add_user_in_department, get_selected_staff_user, remove_user_from_department
from app.create_log import setup_logger
from app.tgbot.loader import dp, bot
from app.db.structure_of_db import User

top_logger: logging.Logger = setup_logger("App.Bot.top", "app/log/h_top.log")


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_admin(),
                    commands="help_top")
@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_top_manager(),
                    commands="help_top")
async def top_help(message: types.Message):
    """
    Выводит помощь для управления сотрудниками
    :param message:
    :return:
    """
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    top_logger.info(f"{user.full_name()} ввёл команду /help_top")
    await message.answer(await get_top_help())


@dp.callback_query_handler(callback_top.filter(action="cancel"))
@dp.callback_query_handler(callback_top_select.filter(action="cancel"))
# @dp.callback_query_handler(callback_top_decision.filter(action="cancel"))
async def top_cancel(call: types.CallbackQuery):
    """
    Удаляет клавиатуру кнопок.
    :param call:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    top_logger.info(f"{user.full_name()} нажал кнопку отмены")
    await call.message.edit_text("Выбор отменён.")


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_admin(),
                    commands="top_menu")
@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_top_manager(),
                    commands="top_menu")
async def top_commands(message: types.Message):
    """
    Выводит меню управленческих команд
    :param message:
    :return:
    """
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    top_logger.info(f"{user.full_name()} ввёл команду /top_manu")
    await message.answer("Выберите позицию, которую хотите назначить", reply_markup=await get_top_menu())


@dp.callback_query_handler(callback_top.filter(action="set_user"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_admin())
@dp.callback_query_handler(callback_top.filter(action="set_user"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_top_manager())
async def select_staff_list(call: types.CallbackQuery, callback_data: dict):
    """
    Выводит меню выбора в какой отдел назначить.
    :param call:
    :param callback_data:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    top_logger.info(f"{user.full_name()} нажал кнопку 'Назначить пользователя'")
    await call.message.edit_text("Выберите позицию, которую хотите назначить",
                                 reply_markup=await get_select_staff("add"))


@dp.callback_query_handler(callback_top.filter(action=["set_constructor", "set_designer",
                                                       "set_electronic", "set_manager",
                                                       "set_graphics"]))
async def select_user_for_add_in_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Выводит клавиатуру пользователей для добавления их в выбранный отдел
    :param call:
    :param callback_data:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    selected_list: str = callback_data.get("action").split("_")[-1]
    ru_type_staff: str = await get_ru_type_staff(selected_list)
    top_logger.info(f"{user.full_name()} нажал кнопку 'Назначить {ru_type_staff}'")
    await call.message.edit_text(f"Выберите пользователя которого хотите назначить на позицию '{ru_type_staff}'",
                                 reply_markup=await get_possible_user(selected_list))


@dp.callback_query_handler(callback_top_select.filter(action=["set_constructor", "set_designer",
                                                              "set_electronic", "set_manager",
                                                              "set_graphics"]))
async def add_user_in_selected_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Добавляет выбранному пользователю user новую должность. И уведомляет его об этом.
    :param call:
    :param callback_data:
    :return:
    """
    top_manager: User = User.get_user_by_telegram_id(call.from_user.id)
    selected_list: str = callback_data.get("action").split("_")[-1]
    user: User = User.get_user(callback_data.get("user_id"))
    ru_name_position: str = await get_ru_type_staff(selected_list)
    top_logger.info(f"{top_manager.full_name()} определяет {user.full_name()}"
                    f" на позицию {ru_name_position}")
    text = f"{await add_user_in_department(user, selected_list)} {ru_name_position}"
    await call.message.edit_text(text)
    await bot.send_message(user.telegram_id, f"Вас поставили на позицию '{ru_name_position}'")


@dp.callback_query_handler(callback_top.filter(action="remove_position"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_admin())
@dp.callback_query_handler(callback_top.filter(action="remove_position"),
                           lambda message: User.get_user_by_telegram_id(message.from_user.id).is_top_manager())
async def select_staff_list_for_remove(call: types.CallbackQuery, callback_data: dict):
    """
    Выводит меню выбора из какого отдела разжаловать.
    :param call:
    :param callback_data:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    top_logger.info(f"{user.full_name()} нажал кнопку 'Разжаловать пользователя'")
    await call.message.edit_text("Выберите позицию, которую хотите разжаловать",
                                 reply_markup=await get_select_staff("remove"))


@dp.callback_query_handler(callback_top.filter(action=["remove_constructor", "remove_designer",
                                                       "remove_electronic", "remove_manager",
                                                       "remove_graphics"]))
async def select_user_for_remove_from_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Выводит клавиатуру пользователей для убирания их из выбранного отдела.
    :param call:
    :param callback_data:
    :return:
    """
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    selected_list: str = callback_data.get("action").split("_")[-1]
    ru_type_staff: str = await get_ru_type_staff(selected_list)
    top_logger.info(f"{user.full_name()} нажал кнопку 'Разжаловать {ru_type_staff}'")
    await call.message.edit_text(f"Выберите пользователя которого хотите снять с позиции '{ru_type_staff}'",
                                 reply_markup=await get_selected_staff_user(selected_list))


@dp.callback_query_handler(callback_top_select.filter(action=["remove_constructor", "remove_designer",
                                                              "remove_electronic", "remove_manager",
                                                              "remove_graphics"]))
async def add_user_in_selected_staff(call: types.CallbackQuery, callback_data: dict):
    """
    Убирает выбранному пользователю user должность. И не уведомляет его об этом.
    :param call:
    :param callback_data:
    :return:
    """
    top_manager: User = User.get_user_by_telegram_id(call.from_user.id)
    selected_list: str = callback_data.get("action").split("_")[-1]
    user: User = User.get_user(callback_data.get("user_id"))
    ru_name_position: str = await get_ru_type_staff(selected_list)
    top_logger.info(f"{top_manager.full_name()} убирает {user.full_name()}"
                    f" с позиции {ru_name_position}")
    text = f"{await remove_user_from_department(user, selected_list)} {ru_name_position}"
    await call.message.edit_text(text)
    # await bot.send_message(user.telegram_id, f"Вас поставили на позицию '{ru_name_position}'")
