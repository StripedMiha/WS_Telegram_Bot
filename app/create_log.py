import logging
import os


log_path = "log"
if os.path.exists(log_path):
    print("Директория %s уже существует" % log_path)
else:
    try:
        os.mkdir(log_path)
    except OSError:
        print("Создать директорию %s не удалось" % log_path)
    else:
        print("Успешно создана директория %s " % log_path)


def setup_logger(name, log_file, level=logging.INFO):
    """To setup as many loggers as you want"""

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
