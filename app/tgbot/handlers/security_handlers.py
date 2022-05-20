import logging
import re
import typing
from pprint import pprint

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from passlib.context import CryptContext

from app.create_log import setup_logger
from app.db.structure_of_db import User
from app.back.user_back import callback_menu, get_keyboard
from app.tgbot.loader import dp, bot

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
                         "Веб версия доступна по ссылке http://192.168.0.237:4400/home")
    await state.finish()
    if user.user_image is None:
        await message.answer("Вы так же можете добавить фото из Telegram.\n"
                             "Для этого введите команду /photo")
    # if user.user_image is None and image is not None:


@dp.message_handler(lambda message: User.get_user_by_telegram_id(message.from_user.id).has_access(),
                    commands='link')
async def get_link(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    if user.hashed_password:
        await message.answer("Ссылка на веб ресурс:\n"
                             "http://192.168.0.237:4400/home")
    else:
        await message.answer("Для получения доступа необходимо сначала задать пароль\n"
                             "Для этого введите команду /set_password")


@dp.message_handler(commands='photo')
async def get_photo(message: types.Message):
    user: User = User.get_user_by_telegram_id(message.from_user.id)
    image = await bot.get_user_profile_photos(user.telegram_id, limit=1)
    if len(image.photos) == 0:
        await message.answer('У вас не установленно фото в телеграм.\n'
                             'Либо ваши настройки приватности не позволяют его взять. 😢')
        return
    image_id = image.photos[0][-1].file_id
    file_path = (await bot.get_file(image_id)).file_path
    result: typing.BinaryIO = await bot.download_file(file_path)
    await bot.send_photo(user.telegram_id,
                         result,
                         'Хотите установить это фото?',
                         reply_markup=await get_keyboard(
                             [["Добавить фото", "add_image"],
                              ["Не добавлять фото", "ignore_image"]],
                             enable_cancel=False)
                         )


@dp.callback_query_handler(callback_menu.filter(action=["add_image", "ignore_image"]))
async def image_decide(call: types.CallbackQuery, callback_data: dict):
    action: str = callback_data.get('action')
    if action == "add_image":
        user: User = User.get_user_by_telegram_id(call.from_user.id)
        image = await bot.get_user_profile_photos(user.telegram_id, limit=1)
        image_id = image.photos[0][-1].file_id
        file_path = (await bot.get_file(image_id)).file_path
        await bot.download_file(file_path, 'app/db/png/profile_image.png')
        user: User = User.get_user_by_telegram_id(call.from_user.id)
        with open('app/db/png/profile_image.png', 'rb') as f:
            user.set_image(f.read())
        await call.message.edit_caption("Фото добавлено")
    else:
        await call.message.edit_caption("Фото не добавлено :с")
