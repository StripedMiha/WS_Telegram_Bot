import logging

import sqlalchemy.exc
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.callback_data import CallbackData


from app.KeyboardDataClass import KeyboardData
from app.back.back_manager import get_manager_menu
from app.create_log import setup_logger
from app.tgbot.loader import dp, bot
from app.db.structure_of_db import User, Status

user_logger: logging.Logger = setup_logger("App.Bot.manager", "app/log/h_manager.log")


class OrderCreateProject(StatesGroup):
    wait_for_project_name = State()
    wait_for_project_description = State()


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).is_manager(),
                    commands="manager_menu")
async def manager_commands(message: types.Message) -> None:
    """
    По команде /manager выводит меню менеджерских команд
    :param message:
    :return: None
    """
    await message.answer("Команды менеджера", reply_markup=await get_manager_menu())
