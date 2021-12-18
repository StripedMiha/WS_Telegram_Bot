import datetime
import logging
import asyncio
import aioschedule

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.create_log import setup_logger

bot: Bot
time_logger: logging.Logger = setup_logger("App.Bot.time", "log/time.log")


def register_handlers_admin(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot


async def noon_print():
    now_hour = datetime.datetime.now().hour
    print('Текущий час -', now_hour)


async def print_second():
    pass
    # print(datetime.datetime.now().second)


async def now_day():
    now_date = datetime.datetime.now().day
    print('Сегодняшнее число - %s' % now_date)


async def time_scanner():
    aioschedule.every(2).hours.do(noon_print)
    aioschedule.every().day.at("00:01").do(now_day)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
