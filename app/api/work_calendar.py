import requests
from datetime import datetime

s = 'https://isdayoff.ru/'


def is_work_day(day: datetime) -> bool:
    link = ''.join([s, day.strftime("%Y%m%d")])
    if int(requests.get(link).content) == 0:
        return True
    else:
        return False
