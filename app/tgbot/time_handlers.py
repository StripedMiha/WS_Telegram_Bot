from datetime import timedelta, datetime
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
from app.db.db_access import get_the_user_costs_for_period
from app.db.stat import show_week_projects_report, projects_report
from app.exceptions import EmptyCost, WrongTime
from app.tgbot.auth import TUser
from app.tgbot.main import get_time_user_notification, get_users_of_list, see_days_costs, set_remind, update_day_costs

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
    now_hour = datetime.now().hour
    print('Текущий час -', now_hour)


# async def print_second():
#     show_week_projects_report()
#     pass


async def week_report(a=1):
    time_logger.info("Пятничный отчёт")
    users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                         [TUser(i.id) for i in get_users_of_list('admin')]
    try:
        min_dates = min(set([i.get_date() for i in users]))
        time_logger.info("Обновляем трудочасы начиная с даты: %s" % min_dates)
        await update_day_costs(min_dates)
    except:
        time_logger.error("Ошибка пятничной статы")
        await bot.send_message(TUser.get_admin_id(), "Ошибка пятничной статы")
    for user in users:
        print(user.full_name)
        if user.notification_status:
            time_logger.info("Пользователь %s не отключал уведомления" % user.full_name)
            try:
                time_logger.info("Генерируем график и получаем часы для %s" % user.full_name)
                sum_costs = projects_report(user)
                time_logger.info("Пользователь %s оформил %s часов" % (user.full_name, sum_costs))
                time_logger.info("Отправляем пользователю %s его стату за неделю" % user.full_name)
                await bot.send_photo(user.user_id, types.InputFile('app/db/png/week_%s.png' % user.full_name),
                                     caption='Распределение ваших %s часов по проектам за неделю' % sum_costs)
            except EmptyCost:
                time_logger.info("Пользователь %s оформил ничего не заполнил" % user.full_name)
                try:
                    time_logger.info("Отправляем пользователю %s сообщение о незаполненности часов" % user.full_name)
                    await bot.send_message(user.user_id, "Вы не заполняли на этой неделе. Нипорядок!")
                except ChatNotFound:
                    time_logger.error("Чат с пользователем %s не найден" % user.full_name)
                    pass
            except WrongTime:
                pass
            except ChatNotFound:
                time_logger.error("Чат с пользователем %s не найден" % user.full_name)
                pass
        else:
            time_logger.info("Пользователь %s отключил уведомления" % user.full_name)


async def day_report_message(user: TUser) -> str:
    now_time: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    text: str = ' '
    if user.notification_status:
        if user.get_notification_time() == now_time:
            time_logger.info("Подготавливаем для %s ежедневный отчёт/напоминание" % user.full_name)
            now_date: str = datetime.now().strftime("%Y-%m-%d")
            costs: list = get_the_user_costs_for_period(user, now_date)
            day_cost_sum: timedelta = timedelta(hours=0)
            for i in costs:
                hours, minutes = i.split(":")
                day_cost_sum += timedelta(hours=int(hours), minutes=int(minutes))
            day_cost_sum: float = day_cost_sum.seconds / 60 / 60
            time_logger.info("Пользователь %s наработал на %s часов" % (user.full_name, day_cost_sum))
            if day_cost_sum >= 12:
                text = "\n\n".join(["Вы либо очень большой молодец, либо где-то переусердствовали."
                                    "\nУ вас за сегодня больше 12 часов. Это законно?", see_days_costs(user)])
            elif day_cost_sum >= 8:
                text = "\n\n".join(["Вы всё заполнили, вы молодец!", see_days_costs(user)])
            elif day_cost_sum > 0:
                text = "\n\n".join(["Вы немного не дотянули до 8 часов!", see_days_costs(user)])
            else:
                text = see_days_costs(user)
        elif user.get_remind_notification_time() == now_time:
            time_logger.info("Пользователь %s откладывал напоминание. Присылаем." % user.full_name)
            text = "Вы отложили напоминание заполнить трудоёмкости. Вот оно!"
            user.set_remind_time(None)
    return text


async def day_report():
    if datetime.now().isoweekday() < 6:
        time_logger.info("Сегодня %s" % datetime.now().strftime("%A"))
        users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                             [TUser(i.id) for i in get_users_of_list('admin')]
        for user in users:
            try:
                text = await day_report_message(user)
                if len(text) <= 10:
                    continue
                if "Ксении" in text or "8 часов" in text:
                    time_logger.info("Пользователь %s не заполнил" % user.full_name)
                    keyboard = get_remind_keyboard(REMIND_BUTTON)
                    await bot.send_message(user.user_id, text, reply_markup=keyboard)
                else:
                    time_logger.info("Пользователь %s заполнил" % user.full_name)
                    await bot.send_message(user.user_id, text)
            except ChatNotFound:
                time_logger.error("Чат с пользователем %s не найден" % user.full_name)
                pass
            except MessageTextIsEmpty:
                time_logger.error("Сообщение пользователю %s пустое" % user.full_name)
                pass
            except AttributeError:
                continue


async def check_costs():
    print('start sinc', datetime.now())
    if datetime.now().isoweekday() < 6:
        users: list[TUser] = [TUser(i.id) for i in get_users_of_list('user')] + \
                             [TUser(i.id) for i in get_users_of_list('admin')]
        for user in users:
            print('sinc user ', user.user_id, user.full_name, datetime.now())
            await update_day_costs(user.get_date())
            await asyncio.sleep(5)
    print('end sinc', datetime.now())


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
    aioschedule.every().friday.at("18:35").do(week_report)
    aioschedule.every().minute.do(day_report)
    # aioschedule.every(1).minutes.do(check_costs)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
