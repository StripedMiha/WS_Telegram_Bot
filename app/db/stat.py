import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import collections


from app.db.db_access import get_all_costs_for_period, get_period_user, get_the_user_projects_time_cost_per_period
from app.exceptions import EmptyCost, WrongTime
from app.tgbot.auth import TUser


def sum_period_time_costs(first_day: str) -> dict:
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    users_costs: list[list[str, str]] = get_all_costs_for_period(first_day)
    for i, j in users_costs:
        users_sum[i] += timedelta(hours=int(j.split(':')[0]),
                                  minutes=int(j.split(':')[1]))
    return users_sum


def get_zero_time() -> timedelta:
    return timedelta(hours=0)


def sum_project_time_costs_for_week(first_day: str, user: TUser) -> collections.defaultdict:
    users = get_the_user_projects_time_cost_per_period(first_day, user)
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    for i, j in users:
        users_sum[i] += timedelta(hours=int(j.split(':')[0]),
                                  minutes=int(j.split(':')[1]))
    return users_sum


def sum_time_costs(user: TUser) -> float:
    pass


def get_first_months_day() -> str:
    now_date = datetime.now()
    return '-'.join([str(now_date.year), str(now_date.month), '01'])


def get_first_week_day() -> str:
    now_date = datetime.now()
    while now_date.isoweekday() > 1:
        now_date = now_date - timedelta(days=1)
    return now_date.strftime("%Y-%m-%d")


def get_f_date(i: int) -> datetime:
    return datetime(month=datetime.now().month, year=datetime.now().year, day=i)


def get_count_work_days() -> int:
    now_day = datetime.now().day
    w = [1 if get_f_date(i).isoweekday() < 6 else 0 for i in range(1, now_day + 1)]
    counter_work_days = sum(w)
    return counter_work_days


def current_month_stat() -> dict:
    first_day: str = get_first_months_day()
    users_sum: dict = sum_period_time_costs(first_day)
    return users_sum


def current_week_stat() -> dict:
    first_day: str = get_first_week_day()
    users_sum: dict = sum_period_time_costs(first_day)
    return users_sum


def user_project_week_stat(user: TUser) -> dict:
    first_day: str = get_first_week_day()
    project_sum: collections.defaultdict = sum_project_time_costs_for_week(first_day, user)
    return project_sum


def to_float(time: timedelta) -> float:
    dtime = timedelta(seconds=time.seconds, days=time.days)
    hours = (dtime.seconds // 60 // 60 + (dtime.seconds // 60 % 60) / 60) + dtime.days * 24
    return hours


def short_project_name(long_name: str) -> str:
    short_name = long_name
    if "Общие задачи" in long_name:
        short_name = "Общие задачи"
    elif re.search(r'[a-z]{3,5}-\d{3}([a-z]\d\d)?', long_name):
        c = re.match(r'[a-z]{3,5}-\d{3}([a-z]\d\d)?', long_name)
        short_name = c.group(0)
    return short_name


def projects_report(user: TUser) -> float:
    now_time: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    # time: list = show_week_projects_report(user)
    # if user.get_notification_time() == now_time:
    time: list = show_week_projects_report(user)
    return sum(time)
    # else:
    #     raise WrongTime


def show_month_gist():
    data = current_month_stat()
    users = [TUser(i).first_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_value = get_count_work_days() * 8
    plt.gcf().clear()
    plt.title('Статистика за текущий календарный месяц')
    plt.axhline(max_value, color='green', label='Эталон')
    # plt.axhline(max_value + 10, color='white')
    plt.legend(loc=1)
    plt.ylabel('часы')
    plt.grid(visible=True)
    step: int = 5 if max_value < 100 else 10
    plt.yticks(np.arange(0, max(time) + 15 if max(time) > max_value else max_value + 15, step=step))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/1')


def show_week_gist():
    data = current_week_stat()
    users = [TUser(i).first_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_value = 5 * 8
    plt.gcf().clear()
    plt.title('Статистика за текущую неделю')
    plt.axhline(max_value, color='green', label='Эталон')
    plt.axhline(max_value + 10, color='white')
    plt.legend(loc=1)
    plt.ylabel('часы')
    plt.yticks(np.arange(0, max(time) + 15 if max(time) > max_value else max_value + 15, step=5))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/2')


def show_week_projects_report(user: TUser):
    data = user_project_week_stat(user)
    projects = [short_project_name(i) for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    plt.gcf().clear()
    plt.plot(kind='pie', subplots=True, figsize=(8, 8), dpi= 80)
    plt.pie(time, labels=projects)
    plt.title("Распределение за неделю")
    plt.savefig('app/db/png/%s_%s' % ('week', user.full_name))
    return time
