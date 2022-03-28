import logging
import asyncio
import os

from aiogram import Bot
from aiogram.types import BotCommand

from app.config_reader import load_config
from app.create_log import setup_logger
from app.start_type import start_from_docker

from app.tgbot.loader import bot
from app.tgbot import *

main_logger: logging.Logger = setup_logger("App.Bot.bot", "app/log/tgbot.log")
bot_logger: logging.Logger = setup_logger("App.Bot", "app/log/bot.log")
app_logger: logging.Logger = setup_logger("App", "app/log/app.log")


async def main_bot():
    main_logger.error("Starting bot")

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    # await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()
    main_logger.info("The bot has started")


# Регистрация команд, отображаемых в интерфейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),
        BotCommand(command="/month", description="Получить месячную статистику"),
        BotCommand(command="/week", description="Получить недельную статистику"),
        BotCommand(command="/report", description="Получить отчёт по дням недели"),
    ]
    await bot.set_my_commands(commands)


async def start():
    m = asyncio.create_task(main_bot())
    t = asyncio.create_task(time_scanner())
    await asyncio.gather(m, t)


# проверка запуска
if __name__ == "__main__":
    from app.tgbot.handlers import dp
    os.system("alembic upgrade head")
    asyncio.run(start())
