import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.config_reader import load_config
from app.create_log import setup_logger

from app.tgbot.administration.admin_handlers import register_handlers_admin
from app.tgbot.time_handlers import time_scanner, register_handlers_time
from app.tgbot.users.stat_handlers import register_handlers_stat
from app.tgbot.users.user_handlers import register_handlers_user, register_handlers_wait_input

main_logger: logging.Logger = setup_logger("App.Bot.bot", "log/tgbot.log")
bot_logger: logging.Logger = setup_logger("App.Bot", "log/bot.log")
app_logger: logging.Logger = setup_logger("App", "log/app.log")


async def main_bot():
    main_logger.error("Starting bot")

    # парсинг файла конфигурации
    config = load_config("config/bot.ini")

    # Объявление и инициализация объектов бота и диспетчера
    bot = Bot(token=config['tg_bot']['token'], parse_mode=types.ParseMode.HTML)
    dp = Dispatcher(bot, storage=MemoryStorage())

    # Регистрация обработчиков
    register_handlers_admin(dp, bot, config['tg_bot']['admin_id'])
    register_handlers_user(dp)
    register_handlers_wait_input(dp, bot, config['tg_bot']['admin_id'])
    register_handlers_stat(dp, bot, config['tg_bot']['admin_id'])
    register_handlers_time(dp, bot, config['tg_bot']['admin_id'])

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()
    main_logger.info("The bot has started")


# Регистрация команд, отображаемых в интерфейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),
        BotCommand(command="/month", description="Получить месячную статистику"),
        BotCommand(command="/week", description="Получить недельную статистику")
    ]
    await bot.set_my_commands(commands)


async def start():
    m = asyncio.create_task(main_bot())
    t = asyncio.create_task(time_scanner())
    await asyncio.gather(m, t)


# проверка запуска
if __name__ == "__main__":
    asyncio.run(start())
