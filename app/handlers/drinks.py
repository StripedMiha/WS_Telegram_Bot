from aiogram import Dispatcher, types
# from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters.state import State, StatesGroup


available_bottle_alcohol_drinks_names = ["Светлое пиво", "Сидр", "Тёмное пиво", "Медовуха"]
available_glasses_alcohol_drinks_names = ["Ром", "Виски", "Джин", "Водка"]
available_bottle_alcohol_drinks_sizes = ["1 бутылку", "2 бутылки", "3 бутылки", "4 бутылки"]
available_glasses_alcohol_drinks_sizes = ["Сок", "Вода", "Газировка", "Квас"]
available_bottle_alcohol_free_drinks_names = ["Энергетик", "Коктельный напиток"]
available_glasses_alcohol_free_drinks_names = ["Сок", "Вода", "Газировка", "Квас"]
# available_bottle_alcohol_free_drinks_sizes = []
# available_glasses_alcohol_free_drinks_sizes = []


async def drinks_start(message: types.Message):
    await message.answer("Пока что недопустпно :С")


def register_handlers_drinks(dp: Dispatcher):
    dp.register_message_handler(drinks_start, commands="drinks", state="*")
