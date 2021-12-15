import datetime
import logging
import asyncio
import re
from os import path

import aioschedule
from aiogram import Bot, Dispatcher, types
from aiogram.utils.callback_data import CallbackData
from aiogram.types import BotCommand, callback_query
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

from app.config_reader import load_config
from app.tgbot.auth import TUser
from app.create_log import setup_logger

from app.tgbot.administration.admin_handlers import register_handlers_admin

from app.tgbot.administration.admin_handlers import get_keyboard_admin
from app.tgbot.users.stat_handlers import register_handlers_stat
from app.tgbot.users.user_handlers import register_handlers_user, register_handlers_wait_input

# config = load_config("config/bot.ini")
# bot = Bot(token=config['tg_bot']['token'], parse_mode=types.ParseMode.HTML)
# dp = Dispatcher(bot, storage=MemoryStorage())
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


    # Регистрация хэндлеров
    register_handlers_admin(dp, bot, config['tg_bot']['admin_id'])
    register_handlers_user(dp)
    register_handlers_wait_input(dp, bot, config['tg_bot']['admin_id'])
    register_handlers_stat(dp, bot, config['tg_bot']['admin_id'])

    # Установка команд бота
    await set_commands(bot)

    # Запуск поллинга
    await dp.skip_updates()  # пропуск накопившихся апдейтов (необязательно)
    await dp.start_polling()
    main_logger.info("The bot has started")
    # await executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


# Регстрация команд, отображаемых в интерефейсе Телеграм
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/menu", description="Взаимодействие с ботом"),
        BotCommand(command="/stat", description="Получить месячную статистику")

    ]
    await bot.set_my_commands(commands)  # TODO наверх


def log_in(*arg):
    time = str(datetime.datetime.today())
    string = time + ' ' + ' '.join([str(i) for i in arg])
    with open('users_messages.txt', 'a', encoding='utf-8') as f:
        print(string, file=f)



async def noon_print():
    five = [i for i in range(0, 60, 1)]
    now_minute = datetime.datetime.now().minute
    if now_minute in five:
        print('Текущая минута - ', now_minute)


async def print_second():
    pass
    # print(datetime.datetime.now().second)


async def now_monday():
    print('сегодня понедельник')

async def on_startup():
    aioschedule.every().minute.do(noon_print)
    aioschedule.every(5).seconds.do(print_second)
    aioschedule.every().monday.at("16:17").do(now_monday)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def start():
    m = asyncio.create_task(main_bot())
    t = asyncio.create_task(on_startup())
    await asyncio.gather(m, t)


# проверка запуска
if __name__ == "__main__":
    asyncio.run(start())
