from datetime import date, datetime, timedelta
from pprint import pp, pprint
import matplotlib.pyplot as plt
import numpy as np


from app.db.db_access import get_all_month_costs, get_months_user
from app.auth import TUser


def sum_month_time_costs(first_day: str):
    users = get_months_user(first_day)
    users_sum = {}
    for i in users:
        users_sum[i] = timedelta(hours=0)
    users_costs: list[list[str, str]] = get_all_month_costs(first_day)

    for i, j in users_costs:
        users_sum[i] += timedelta(hours=int(j.split(':')[0]),
                                  minutes=int(j.split(':')[1]))
    return users_sum


def get_first_months_day() -> str:
    now_date = datetime.now()
    return '-'.join([str(now_date.year), str(now_date.month), '01'])


def get_f_date(i: int) -> datetime:
    return datetime(month=datetime.now().month, year=datetime.now().year, day=i)


def get_count_work_days() -> int:
    now_day = datetime.now().day
    w = [1 if get_f_date(i).isoweekday() < 6 else 0 for i in range(1, now_day + 1)]
    counter_work_days = sum(w)
    return counter_work_days


def current_month_stat():
    first_day = get_first_months_day()
    users_sum = sum_month_time_costs(first_day)
    return users_sum


def to_float(time: timedelta) -> float:
    dtime = timedelta(seconds=time.seconds, days=time.days)
    hours = (dtime.seconds // 60 // 60 + (dtime.seconds // 60 % 60) / 60) + dtime.days * 24
    return hours


def show_gist():
    data = current_month_stat()
    users = [TUser(i).first_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    max_value = get_count_work_days() * 8
    plt.gcf().clear()
    plt.title('Статистика за текущий календарный месяц')
    plt.axhline(max_value, color='green', label='Эталон')
    plt.axhline(max_value + 10, color='white')
    plt.legend()
    plt.ylabel('часы')
    plt.yticks(np.arange(0, max(time) + 15 if max(time) > max_value else max_value + 15, step=5))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/1')



