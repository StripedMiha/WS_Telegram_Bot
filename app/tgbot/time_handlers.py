import datetime
import logging
import asyncio
from pprint import pprint

from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import ChatNotFound, MessageTextIsEmpty
import aioschedule

from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.create_log import setup_logger
from app.db.stat import show_week_projects_report, projects_report
from app.exceptions import EmptyCost, WrongTime
from app.tgbot.auth import TUser
from app.tgbot.main import get_time_user_notification, get_users_of_list, see_days_costs, day_report_message, \
    set_remind, update_day_costs

bot: Bot
time_logger: logging.Logger = setup_logger("App.Bot.time", "log/time.log")


def register_handlers_time(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot
    dp.register_message_handler(week_report, lambda message: message.text.lower() == "test")
    dp.register_callback_query_handler(delay_remind, callback_time.filter(action="remind"))
    dp.register_callback_query_handler(remind_cancel, callback_time.filter(action="cancel"))


callback_time = CallbackData("fab_time", "action", "time")
REMIND_BUTTON = [["Напомнить через 10 минут", "0.10", "remind"],
                 ["Напомнить через 1 час", "1.00", "remind"],
                 ["Напомнить через 3 часа", "3.00", "remind"]]


# Формирование инлайн клавиатуры отложенных напоминаний
def get_remind_keyboard(list_data: list[list], width: int = 2,
                        enable_cancel: bool = True) -> types.InlineKeyboardMarkup:
    buttons = []
    for name, time, action in list_data:
        buttons.append(types.InlineKeyboardButton(text=name, callback_data=callback_time.new(action=action,
                                                                                             time=time)))
    if enable_cancel:
        buttons.append(types.InlineKeyboardButton(text="Отмена", callback_data=callback_time.new(action="cancel",
                                                                                                 time="---")))
    keyboard = types.InlineKeyboardMarkup(row_width=width)
    keyboard.add(*buttons)
    return keyboard


async def noon_print():
    now_hour = datetime.datetime.now().hour
    print('Текущий час -', now_hour)


async def print_second():
    show_week_projects_report()
    pass


async def week_report(a=1):
    users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                         [TUser(i.id) for i in get_users_of_list('admin')]
    try:
        min_dates = min(set([i.get_date() for i in users]))
        await update_day_costs(min_dates)
    except:
        await bot.send_message(TUser.get_admin_id(), "Ошибка пятничной статы")
    for user in users:
        print(user.full_name)

        if user.notification_status:
            try:
                sum_costs = projects_report(user)
                await bot.send_photo(user.user_id, types.InputFile('app/db/png/week_%s.png' % user.full_name),
                                     caption='Распределение ваших %s часов по проектам за неделю' % sum_costs)
            except EmptyCost:
                try:
                    await bot.send_message(user.user_id, "Вы не заполняли на этой неделе. Нипорядок!")
                except ChatNotFound:
                    pass
            except WrongTime:
                pass
            except ChatNotFound:
                pass


async def day_report():
    if datetime.datetime.now().isoweekday() < 6:
        users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                             [TUser(i.id) for i in get_users_of_list('admin')]
        for user in users:
            try:
                text = await day_report_message(user)
                if len(text) <= 10:
                    continue
                if "Ксении" in text or "8 часов" in text:
                    keyboard = get_remind_keyboard(REMIND_BUTTON)
                    await bot.send_message(user.user_id, text, reply_markup=keyboard)
                else:
                    await bot.send_message(user.user_id, text)
            except ChatNotFound:
                pass
            except MessageTextIsEmpty:
                pass
            except AttributeError:
                continue


async def check_costs():
    print('start sinc', datetime.datetime.now())
    if datetime.datetime.now().isoweekday() < 6:
        users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                             [TUser(i.id) for i in get_users_of_list('admin')]
        for user in users:
            print('sinc user ', user.user_id, user.full_name, datetime.datetime.now())
            await update_day_costs(user.get_date())
            await asyncio.sleep(5)
    print('end sinc', datetime.datetime.now())


async def remind_cancel(call: types.CallbackQuery, callback_data: dict):
    time_logger.info("%s не будет откладывать напоминание" % call.from_user.full_name)
    await call.message.edit_text("А вы рисковый!")


async def delay_remind(call: types.CallbackQuery, callback_data: dict):
    user: TUser = TUser(call.from_user.id)
    text = await set_remind(user, callback_data.get("time"), call.message.date)
    await call.message.edit_text(text)


async def get_time():
    return await get_time_user_notification()


async def time_scanner():
    aioschedule.every().thursday.at("19:00").do(week_report)
    aioschedule.every().minute.do(day_report)
    # aioschedule.every(1).minutes.do(check_costs)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
