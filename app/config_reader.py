import configparser


def load_config(path: str):
    config = configparser.ConfigParser()
    config.read(path)
    return config
