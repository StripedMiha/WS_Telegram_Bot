import logging

from aiogram import Bot, Dispatcher, types

from app.create_log import setup_logger
from app.db.stat import show_week_report
from app.exceptions import EmptyCost
from app.tgbot.auth import TUser
from app.tgbot.main import get_month_stat, get_week_stat, get_week_report_gist

bot: Bot
stat_logger: logging.Logger = setup_logger("App.Bot.stat", "app/log/stat.log")


def register_handlers_stat(dp: Dispatcher, main_bot: Bot, admin_id: int):
    global bot
    bot = main_bot
    dp.register_message_handler(stat_month, commands="month")
    dp.register_message_handler(stat_week, commands="week")
    dp.register_message_handler(get_week_report, commands="report")
    # dp.register_message_handler(day_report, lambda message: message.text.lower() == "test")


# Первая версия статистики
async def stat_month(message: types.Message):
    stat_logger.info("%s ввёл команду /month" % message.from_user.full_name)
    try:
        get_month_stat()
    except EmptyCost:
        await message.answer("В этом месяце никто ещё не заполнял через бота :с")
        return
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/1.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')


async def stat_week(message: types.Message):
    stat_logger.info("%s ввёл команду /week" % message.from_user.full_name)
    try:
        get_week_stat()
    except EmptyCost:
        await message.answer("На этой неделе никто ещё не заполнял через бота :с")
        return
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/2.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')


async def get_week_report(message: types.Message):
    stat_logger.info("%s ввёл команду /report" % message.from_user.full_name)
    user: TUser = TUser(message.from_user.id)
    try:
        await get_week_report_gist(user)
    except Exception as err:
        await message.answer("Происходит некоторая ошибка. Сообщите о ней Мишане")
        print(err.args)
        await bot.send_message(TUser.get_admin_id(), "У %s ошибка графика недельного отчёта" % user.full_name)
        stat_logger.error("Ошибка %s" % err)
        return
    await bot.send_photo(user.user_id, types.InputFile("app/db/png/%s_%s.png" % ('report', user.full_name)))
    stat_logger.info("%s Успешно получил отчёт за неделю" % user.full_name)
