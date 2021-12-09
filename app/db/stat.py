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


def current_month_stat():
    now_date = datetime.now()
    first_day = '-'.join([str(now_date.year), str(now_date.month), '01'])
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
    plt.gcf().clear()
    # fig, ax = plt.subplots(figsize=(5, 3))
    plt.title('Статистика за текущий календарный месяц')
    # ax.set_ylabel('часы')
    # fig.tight_layout()
    plt.ylabel('часы')
    plt.yticks(np.arange(0, max(time)+5, step=5))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/1')









