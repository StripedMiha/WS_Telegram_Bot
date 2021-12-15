import configparser
from dataclasses import dataclass


@dataclass
class TgBot:
    token: str
    admin_id: int


class WsKey:
    api_key: str
    url: str


@dataclass
class Config:
    tg_bot: TgBot


def load_config(path: str):
    config = configparser.ConfigParser()
    config.read(path)
    return config


# def load_config(path: str):
#     config = configparser.ConfigParser()
#     config.read(path)
#
#     tg_bot = config["tg_bot"]
#
#     return Config(
#         tg_bot=TgBot(
#             token=tg_bot["token"],
#             admin_id=int(tg_bot["admin_id"])
#         )
#     )

