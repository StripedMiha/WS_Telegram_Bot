import logging

from aiogram import Bot, Dispatcher, types

from app.create_log import setup_logger
from app.tgbot.main import get_month_stat

bot: Bot
stat_logger: logging.Logger = setup_logger("App.Bot.stat", "log/stat.log")


def register_handlers_stat(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot
    dp.register_message_handler(cmd_stat, commands="stat")


# Первая версия статистики
async def cmd_stat(message: types.Message):
    stat_logger.info("%s ввёл команду /stat" % message.from_user.full_name)
    get_month_stat()
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/1.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')
