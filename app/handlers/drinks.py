from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


available_bottle_alcohol_drinks_names = ["Светлое пиво", "Сидр", "Тёмное пиво", "Медовуха"]
available_glasses_alcohol_drinks_names = ["Ром", "Виски", "Джин", "Водка"]
available_bottle_drinks_sizes = ["1 бутылку", "2 бутылки", "3 бутылки", "4 бутылки"]
available_glasses_drinks_sizes = ["Только попробовать", "1 стакан", "2 стакана", "3 стакана", "Слишком много"]
available_bottle_alcohol_free_drinks_names = ["Энергетик", "Коктельный напиток"]
available_glasses_alcohol_free_drinks_names = ["Сок", "Вода", "Газировка", "Квас", "Гейская пинаколада"]


class OrderDrinks(StatesGroup):
    waiting_for_drinks_type = State()
    waiting_for_drinks_name = State()
    waiting_for_drinks_size = State()


async def drinks_start(message: types.Message):
    # await message.answer("Пока что недопустпно :С")
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Алкогольный")
    keyboard.add("Безалкогольный")
    keyboard.add("Отмена")
    await message.answer("Выберите тип напитка", reply_markup=keyboard)
    await OrderDrinks.waiting_for_drinks_type.set()


async def drinks_type_chosen(message: types.Message, state: FSMContext):
    if message.text not in ["Алкогольный", "Безалкогольный"]:
        await message.answer("Пожалуйста, выберите тип напитка, используя клавиатуру ниже.")
        return
    if message.text == "Алкогольный" or message.text == "Безалкогольный":
        await state.update_data(chosen_drink_type=message.text)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    user_data = await state.get_data()
    if user_data['chosen_drink_type'] == "Алкогольный":
        for drink in available_bottle_alcohol_drinks_names:
            keyboard.add(drink)
        for drink in available_glasses_alcohol_drinks_names:
            keyboard.add(drink)
    elif user_data['chosen_drink_type'] == "Безалкогольный":
        for drink in available_bottle_alcohol_free_drinks_names:
            keyboard.add(drink)
        for drink in available_glasses_alcohol_free_drinks_names:
            keyboard.add(drink)
    keyboard.add("Отмена")
    await message.answer("Выберите напиток:", reply_markup=keyboard)
    await OrderDrinks.waiting_for_drinks_name.set()


async def drinks_name_chosen(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    if user_data["chosen_drink_type"] == "Алкогольный":
        if message.text not in available_bottle_alcohol_drinks_names + available_glasses_alcohol_drinks_names:
            await message.answer("Пожалуйста, выберите напиток, используя клавиатуру ниже.")
            return
    elif user_data['chosen_drink_type'] == "Безалкогольный":
        if message.text not in available_bottle_alcohol_free_drinks_names + available_glasses_alcohol_free_drinks_names:
            await message.answer("Пожалуйста, выберите напиток, используя клавиатуру ниже.")
            return
    await state.update_data(chosen_drink_name=message.text)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.text in available_glasses_alcohol_drinks_names + available_glasses_alcohol_free_drinks_names:
        for size in available_glasses_drinks_sizes:
            keyboard.add(size)
    else:
        for size in available_bottle_drinks_sizes:
            keyboard.add(size)
    keyboard.add("Отмена")
    await OrderDrinks.next()
    await message.answer("Выберите обьёмы для употребления:", reply_markup=keyboard)


async def drinks_size_chosen(message: types.Message, state: FSMContext):
    if message.text not in available_glasses_drinks_sizes + available_bottle_drinks_sizes:
        await message.answer("Пожалуйста, выберите обьёмы, используя клавиатуру ниже.")
        return
    user_data = await state.get_data()
    answer = f"Вы заказали {user_data['chosen_drink_name']} в количестве {message.text}."
    if user_data['chosen_drink_type'] == "Алкогольный":
        answer += f"\nБудьте осторожны, алкоголь вредит вашему здоровью!!!"
    if user_data['chosen_drink_name'] == 'Энергетик' and message.text != '1 бутылку':
        answer += f"\nБудьте крайне осторожны, есть вероятность увидеть время"
    await message.answer(answer, reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


def register_handlers_drinks(dp: Dispatcher):
    dp.register_message_handler(drinks_start, commands="drinks", state="*")
    dp.register_message_handler(drinks_type_chosen, state=OrderDrinks.waiting_for_drinks_type)
    dp.register_message_handler(drinks_name_chosen, state=OrderDrinks.waiting_for_drinks_name)
    dp.register_message_handler(drinks_size_chosen, state=OrderDrinks.waiting_for_drinks_size)
