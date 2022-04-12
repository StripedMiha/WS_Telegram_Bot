import requests
from datetime import datetime

s = 'https://isdayoff.ru/'


def is_work_day(day: datetime) -> bool:
    link = ''.join([s, day.strftime("%Y%m%d")])
    if int(requests.get(link).content) == 0:
        return True
    else:
        return False


def count_work_day() -> int:
    now_day: datetime = datetime.now()
    first_day: str = now_day.strftime('%Y%m')
    last_day: str = now_day.strftime('%Y%m%d')
    m: str = f"https://isdayoff.ru/api/getdata?date1={first_day}01&date2={last_day}"
    return m.count('0')
