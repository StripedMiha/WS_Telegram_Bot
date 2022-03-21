from datetime import timedelta, datetime
import logging
import asyncio
from pprint import pprint

from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import ChatNotFound, MessageTextIsEmpty, BotBlocked
import aioschedule

from aiogram import Bot, Dispatcher, types

from app.api.work_calendar import is_work_day
from app.create_log import setup_logger
from app.db.stat import projects_report
from app.db.structure_of_db import User, Status
from app.exceptions import EmptyCost, WrongTime, EmptyDayCosts, NotUserTime, NoRemindNotification
from app.tgbot.main import set_remind, update_day_costs, get_text_for_empty_costs, day_report_message

bot: Bot
time_logger: logging.Logger = setup_logger("App.Bot.time", "app/log/time.log")


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


async def week_report(a=1):
    time_logger.info("Пятничный отчёт")
    users: list[User] = Status.get_users('user')
    try:
        min_dates = min(set([i.get_date() for i in users]))
        time_logger.info("Обновляем трудочасы начиная с даты: %s" % min_dates)
        await update_day_costs(min_dates)
    except:
        time_logger.error("Ошибка пятничной статистики")
        await bot.send_message(User.get_admin_id(), "Ошибка пятничной статистики")
    for user in users:
        if user.notification_status:
            time_logger.info("Пользователь %s не отключал уведомления" % user.full_name())
            try:
                time_logger.info("Генерируем график и получаем часы для %s" % user.full_name())
                sum_costs = projects_report(user)
                time_logger.info("Пользователь %s оформил %s часов" % (user.full_name(), sum_costs))
                time_logger.info("Отправляем пользователю %s его статистику за неделю" % user.full_name())
                await bot.send_photo(user.user_id, types.InputFile('app/db/png/week_%s.png' % user.full_name()),
                                     caption='Распределение ваших %s часов по проектам за неделю' % sum_costs)
            except EmptyCost:
                time_logger.info("Пользователь %s оформил ничего не заполнил" % user.full_name())
                try:
                    time_logger.info("Отправляем пользователю %s сообщение о незаполненности часов" % user.full_name())
                    await bot.send_message(user.user_id, "Вы не заполняли на этой неделе. Нипорядок!")
                except ChatNotFound:
                    time_logger.error("Чат с пользователем %s не найден" % user.full_name())
                    pass
                except BotBlocked:
                    time_logger.error("Пользователь %s заблокировал бота" % user.full_name())
                    pass
            except WrongTime:
                pass
            except ChatNotFound:
                time_logger.error("Чат с пользователем %s не найден" % user.full_name())
                pass
            except BotBlocked:
                time_logger.error("Пользователь %s заблокировал бота" % user.full_name())
                pass
        else:
            time_logger.info("Пользователь %s отключил уведомления" % user.full_name())


async def day_report():
    if is_work_day(datetime.now()):
        users: list[User] = Status.get_users('user')
        for user in users:
            try:
                text, sum_costs = await day_report_message(user)
                if 0 < sum_costs < 8:
                    time_logger.info("Пользователь %s заполнил меньше 8 часов" % user.full_name)
                    keyboard = get_remind_keyboard(REMIND_BUTTON)
                    await bot.send_message(user.user_id, text, reply_markup=keyboard)
                else:
                    time_logger.info("Пользователь %s заполнил" % user.full_name)
                    await bot.send_message(user.user_id, text)
            except NotUserTime:
                continue
            except EmptyDayCosts:
                time_logger.info("Пользователь %s не заполнил" % user.full_name)
                keyboard = get_remind_keyboard(REMIND_BUTTON)
                try:
                    await bot.send_message(user.user_id, get_text_for_empty_costs(user.get_date()),
                                           reply_markup=keyboard)
                except ChatNotFound:
                    time_logger.error("Чат с пользователем %s не найден" % user.full_name)
                except BotBlocked:
                    time_logger.error("Пользователь %s заблокировал бота" % user.full_name)
            except ChatNotFound:
                time_logger.error("Чат с пользователем %s не найден" % user.full_name)
            except BotBlocked:
                time_logger.error("Пользователь %s заблокировал бота" % user.full_name)
            except MessageTextIsEmpty:
                time_logger.error("Сообщение пользователю %s пустое" % user.full_name)
            except NoRemindNotification:
                continue


async def check_costs():
    print('start sinc', datetime.now())
    if datetime.now().isoweekday() < 6:
        users: list[User] = Status.get_users('user')
        for user in users:
            print('sinc user ', user.user_id, user.full_name, datetime.now())
            await update_day_costs(user.get_date())
            await asyncio.sleep(5)
    print('end sinc', datetime.now())


async def remind_cancel(call: types.CallbackQuery, callback_data: dict):
    time_logger.info("%s не будет откладывать напоминание" % call.from_user.full_name)
    mes_text = call.message.text
    await call.message.edit_text(mes_text)
    await call.message.answer("А вы рисковый!")


async def delay_remind(call: types.CallbackQuery, callback_data: dict):
    user: User = User.get_user_by_telegram_id(call.from_user.id)
    text = await set_remind(user, callback_data.get("time"), call.message.date)
    mes_text = call.message.text
    await call.message.edit_text(mes_text)
    await call.message.answer(text)


async def time_scanner():
    aioschedule.every().friday.at("18:40").do(week_report)
    aioschedule.every().minute.do(day_report)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)
