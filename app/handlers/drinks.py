from aiogram import Dispatcher, types
# from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup


async def drinks_start(message: types.Message):
    await message.answer("Пока что недопустпно :С")


def register_handlers_drinks(dp: Dispatcher):
    dp.register_message_handler(drinks_start, commands="drinks", state="*")
