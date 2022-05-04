import logging

from aiogram import types

from app.back.stat import create_graf
from app.create_log import setup_logger
from app.db.structure_of_db import User
from app.exceptions import EmptyCost
from app.back.main import get_month_stat, get_week_stat, get_week_report_gist
from app.tgbot.loader import dp, bot

stat_logger: logging.Logger = setup_logger("App.Bot.stat", "app/log/stat.log")


# Первая версия статистики
@dp.message_handler(commands="month")
async def stat_month(message: types.Message):
    stat_logger.info("%s ввёл команду /month" % message.from_user.full_name)
    try:
        get_month_stat()
    except EmptyCost:
        await message.answer("В этом месяце никто ещё не заполнял через бота :с")
        return
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/1.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')


@dp.message_handler(commands="week")
async def stat_week(message: types.Message):
    stat_logger.info("%s ввёл команду /week" % message.from_user.full_name)
    try:
        get_week_stat()
    except EmptyCost:
        await message.answer("На этой неделе никто ещё не заполнял через бота :с")
        return
    await bot.send_photo(message.from_user.id, types.InputFile('app/db/png/2.png'),
                         caption='В графике отображены только те часы, которые были занесены через бота')


@dp.message_handler(commands="report")
async def get_week_report(message: types.Message):
    stat_logger.info("%s ввёл команду /report" % message.from_user.full_name)
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    try:
        await get_week_report_gist(user)
    except Exception as err:
        await message.answer("Происходит некоторая ошибка. Сообщите о ней Мишане")
        print(err.args)
        await bot.send_message(User.get_admin_id(), "У %s ошибка графика недельного отчёта" % user.full_name())
        stat_logger.error("Ошибка %s" % err)
        return
    await bot.send_photo(user.telegram_id, types.InputFile("app/db/png/%s_%s.png" % ('report', user.full_name())))
    stat_logger.info("%s Успешно получил отчёт за неделю" % user.full_name())


@dp.message_handler(commands="atata")
@dp.message_handler(commands="атата")
@dp.message_handler(lambda message: "atata" in message.text.lower())
@dp.message_handler(lambda message: "атата" in message.text.lower())
async def atata_report(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    stat_logger.info(f"{user.full_name()} запросил стату 'атата'")
    new_message: types.Message = await bot.send_message(user.telegram_id, "Секунду")
    await create_graf()
    await bot.send_document(user.telegram_id, types.InputFile("app/db/png/atata.png"))
    await new_message.delete()
