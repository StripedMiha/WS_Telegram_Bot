from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app.config_reader import load_config
from app.start_type import start_from_docker

if start_from_docker:
    config = load_config("/run/secrets/bot")
else:
    config = load_config("app/keys/bot.ini")

# Объявление и инициализация объектов бота и диспетчера
bot = Bot(token=config['tg_bot']['token'], parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())
