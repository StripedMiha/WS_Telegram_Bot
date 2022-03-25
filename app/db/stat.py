import re
from datetime import datetime, timedelta
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
import collections

from app.api.work_calendar import is_work_day
from app.db.db_access import get_all_costs_for_period, get_the_user_projects_time_cost_per_period, \
    get_user_costs_per_week
from app.db.structure_of_db import Comment, User
from app.exceptions import EmptyCost


def sum_period_time_costs(first_day: str) -> dict:
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    users_costs: list[list[str, str]] = get_all_costs_for_period(first_day)
    for i, j in users_costs:
        users_sum[i] += timedelta(hours=int(j.split(':')[0]),
                                  minutes=int(j.split(':')[1]))
    return users_sum


def get_zero_time() -> timedelta:
    return timedelta(hours=0)


def sum_project_time_costs_for_week(first_day: str, user: User) -> collections.defaultdict:
    users = get_the_user_projects_time_cost_per_period(first_day, user)
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    for i, j in users:
        users_sum[i] += timedelta(hours=int(j.split(':')[0]),
                                  minutes=int(j.split(':')[1]))
    return users_sum


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
    w = [1 if is_work_day(get_f_date(i)) else 0 for i in range(1, now_day + 1)]
    counter_work_days = sum(w)
    return counter_work_days


def current_month_stat() -> dict:
    first_day: str = get_first_months_day()
    users_sum: dict = sum_period_time_costs(first_day)
    return users_sum


def current_week_stat() -> dict:
    first_day: str = get_first_week_day()
    print(first_day)
    users_sum: dict = sum_period_time_costs(first_day)
    pprint(users_sum)
    return users_sum


def user_project_week_stat(user: User) -> dict:
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


def projects_report(user: User) -> float:
    now_time: str = datetime.now().strftime("%Y-%m-%d %H:%M")
    # time: list = show_week_projects_report(user)
    # if user.get_notification_time() == now_time:
    time: list = show_week_projects_report(user)
    return sum(time)
    # else:
    #     raise WrongTime


def sort_key(l):
    weekdays: dict = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7
    }
    return weekdays[l[0]]


def get_list_times() -> list:
    return [get_zero_time(), get_zero_time()]


def user_week_data(user: User) -> collections.defaultdict:
    first_day: str = get_first_week_day()
    comments: list[Comment] = get_user_costs_per_week(first_day, user)
    week_comments: collections.defaultdict = collections.defaultdict(get_list_times)
    for i in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        week_comments[i] = get_list_times()
    for comment in comments:
        weekday = comment.date.strftime("%A")
        str_time = comment.time.split(":")
        time: timedelta = timedelta(hours=int(str_time[0]), minutes=int(str_time[1]))
        if comment.via_bot:
            week_comments[weekday][0] += time
        week_comments[weekday][1] += time
    coms = []
    for i, j in week_comments.items():
        c = [i, j[0], j[1]]
        coms.append(c)
    coms.sort(key=sort_key)
    return coms
    # comments[-1].date.strftime("%A")


def show_month_gist():
    data = current_month_stat()
    users: list[str] = [User.get_user(i).first_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_value = get_count_work_days() * 8
    plt.gcf().clear()
    plt.title('Статистика за текущий календарный месяц')
    plt.axhline(max_value, color='green', label='Эталон')
    # plt.axhline(max_value + 10, color='white')
    for i in range(16, max_value-1, 8):
        plt.axhline(i, color='grey')
    plt.axhline(8, color='grey', label='День')
    plt.legend(loc=1)
    plt.ylabel('часы')
    # plt.grid(visible=True)
    step: int = 5 if max_value < 100 else 10
    plt.yticks(np.arange(0, max(time) + 15 if max(time) > max_value else max_value + 15, step=step))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/1')


def show_week_gist():
    data = current_week_stat()
    users: list[str] = [User.get_user(i).first_name for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_value = 5 * 8
    plt.gcf().clear()
    plt.title('Статистика за текущую неделю')
    plt.axhline(max_value, color='green', label='Эталон')
    for i in [8, 16, 24]:
        plt.axhline(i, color='grey')
    plt.axhline(32, color='grey', label='День')
    plt.legend(loc=1)
    plt.ylabel('часы')
    plt.yticks(np.arange(0, max(time) + 15 if max(time) > max_value else max_value + 15, step=5))
    plt.xticks(rotation=0)
    plt.bar(users, time)
    plt.savefig('app/db/png/2')


def show_week_projects_report(user: User):
    data = user_project_week_stat(user)
    projects = [short_project_name(i) for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    plt.gcf().clear()
    plt.plot(kind='pie', subplots=True, figsize=(8, 8), dpi=80)
    plt.pie(time, labels=projects)
    plt.title("Распределение за неделю")
    plt.savefig('app/db/png/%s_%s' % ('week', user.full_name()))
    return time


def show_week_report(user: User):
    coms = user_week_data(user)
    days: list = [i[0] for i in coms]
    via_bot: list = [to_float(i[1]) for i in coms]
    via_ws: list = [to_float(i[2]) for i in coms]
    fig, ax = plt.subplots()
    width = 0.5
    x = np.arange(len(days))
    plt.bar(x + 0.025, via_bot, width - 0.1, color="#29A0DC", label="Через бота")
    plt.bar(x + width - 0.025, via_ws, width - 0.1, color="#82C018", label="Всего оформлено")
    plt.axhline(8, color='grey', label='Эталон')
    plt.ylabel("часы")
    max_value = 9 if max(via_ws) <= 8 else max(via_ws) + 1
    plt.ylim(0, max_value)
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(days)
    plt.xlabel("Дни недели")
    plt.title("Заполнение за неделю")
    plt.legend()
    plt.grid(axis="y", linestyle=":")
    plt.savefig('app/db/png/%s_%s.png' % ('report', user.full_name()))
