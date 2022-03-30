import logging

from aiogram import types
import aiogram.utils.exceptions
from aiogram.utils.exceptions import ChatNotFound, BotBlocked, ChatIdIsEmpty, TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError

from app.db.structure_of_db import User
from app.tgbot.loader import dp, bot
from app.create_log import setup_logger

error_logger: logging.Logger = setup_logger("App.Bot.error", "app/log/h_error.log")


@dp.errors_handler()
async def errors_handler(update, exception):
    """

    :param update:
    :param exception:
    :return:
    """

    if isinstance(exception, ChatIdIsEmpty):
        error_logger.error(exception)
        await bot.send_message(User.get_admin_id(), f"Ошибка ChatIdIsEmpty")
        return True

    if isinstance(exception, TelegramAPIError):
        error_logger.error(exception)
        await bot.send_message(User.get_admin_id(), f"Ошибка aiogram:\n{exception}")
        # return True

    if isinstance(exception, SQLAlchemyError):
        error_logger.error(exception)
        await bot.send_message(User.get_admin_id(), f"Ошибка sqlalchemy:\n{exception}")
        # return True

