from datetime import date, datetime, timedelta
import matplotlib.pyplot as plt


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
    dtime = timedelta(seconds=time.seconds)
    hours = dtime.seconds // 60 // 60 + (dtime.seconds // 60 % 60) / 60
    return hours


def show_gist():
    data = current_month_stat()
    users = [TUser(i).full_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    print(data)
    print(time)
    plt.gcf().clear()
    plt.title('Статистика за текущий календарный месяц')
    plt.bar(users, time)
    plt.savefig('app/db/png/1')









