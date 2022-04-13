import requests
from datetime import datetime


def is_work_day(day: datetime) -> bool:
    m: str = f"https://isdayoff.ru/api/getdata?year={day.year}&month={day.month}&day={day.day}"
    req: int = int(requests.get(m).content)
    ans = True if req == 0 or req == 2 or req == 4 else False
    return ans


def count_work_day() -> int:
    now_day: datetime = datetime.now()
    first_day: str = now_day.strftime('%Y%m')
    last_day: str = now_day.strftime('%Y%m%d')
    m: str = f"https://isdayoff.ru/api/getdata?date1={first_day}01&date2={last_day}"
    return m.count('0')
