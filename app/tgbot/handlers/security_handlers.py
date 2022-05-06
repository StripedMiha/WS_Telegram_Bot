import logging
import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from passlib.context import CryptContext

from app.create_log import setup_logger
from app.db.structure_of_db import User
from app.tgbot.loader import dp

security_logger: logging.Logger = setup_logger("App.Bot.security", "app/log/security.log")

PASSWORD_PATTERN = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'

pwd_context: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OrderSecurity(StatesGroup):
    wait_for_password = State()
    wait_dor_confirm_password = State()


def verify_password(plain_password, hashed_password):

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


@dp.message_handler(commands="set_password")
async def start_password_set(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if user.hashed_password:
        await message.answer("У вас уже задан пароль. Для сборса пароля свяжитесь с разработчиком.")
        return
    elif not user.email:
        await message.answer("У вас не установлена почта. Невозможно создать пароль.")
        return
    await message.answer("Введите пароль.")
    await OrderSecurity.wait_for_password.set()


@dp.message_handler(state=OrderSecurity.wait_for_password)
async def input_first_password(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if message.text.lower() in ["cancel", "отмена"]:
        await message.answer("Ввода пароля отменён.")
        await state.finish()
        return
    possible_password = message.text.strip(" ")
    if re.match(PASSWORD_PATTERN, possible_password):
        await state.update_data(hashed_password=get_password_hash(possible_password))
        await message.answer("Введите пароль ещё раз для подтверждения.")
        await OrderSecurity.wait_dor_confirm_password.set()
    else:
        await message.answer("Введённый пароль не отвечает требованиям сложности.\n"
                             "Пароль должен отвечать следующим условиям:\n"
                             "1) Должен содержать как минимум одну строчную букву\n"
                             "2) Должен содержать как минимум одну заглавную букву\n"
                             "3) Должен содержать как минимум одну цифру\n"
                             "4) Должен содержать как минимум 8 символов")


@dp.message_handler(state=OrderSecurity.wait_dor_confirm_password)
async def input_second_password(message: types.Message, state: FSMContext):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if message.text.lower() in ["cancel", "отмена"]:
        await message.answer("Подтверждение пароля отменено.")
        await state.finish()
        return
    possible_password = message.text.strip(" ")
    saved_first_password: str = (await state.get_data()).get("hashed_password")
    if not verify_password(possible_password, saved_first_password):
        await message.answer("Пароли не совпадают. Отмена создания пароля")
        await state.finish()
        return
    user.set_hashed_password(get_password_hash(possible_password))
    await message.answer("Пароль успешно создан.\n"
                         "Веб версия доступна по ссылке localhost:4400/home")
    await state.finish()
