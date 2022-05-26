"""
В этом модуле собираются графики
"""
import re
from datetime import datetime, timedelta, date
from pprint import pprint
from typing import Optional
import collections

import matplotlib.pyplot as plt
import numpy as np

from app.api.work_calendar import count_work_day, get_work_day
from app.db.db_access import get_all_costs_for_period, get_the_user_projects_time_cost_per_period, \
    get_user_costs_per_week
from app.db.structure_of_db import Comment, User, Status
from app.exceptions import EmptyCost


def sum_period_time_costs(first_day: str) -> dict:
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    users_costs: list[list[str, str]] = get_all_costs_for_period(first_day)
    for i, j in users_costs:
        users_sum[i] += j
    return users_sum


def get_zero_time() -> timedelta:
    return timedelta(hours=0)


def sum_project_time_costs_for_week(first_day: str, user: User) -> collections.defaultdict:
    users: list[list[str, str, timedelta]] = get_the_user_projects_time_cost_per_period(first_day, user)
    users_sum: collections.defaultdict = collections.defaultdict(get_zero_time)
    for i, k, j in users:
        i: Optional[str]
        k: Optional[str]
        j: timedelta
        name = i if i else k
        users_sum[name] += j
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


def get_count_work_month_days() -> int:
    counter_work_days: int = count_work_day()
    return counter_work_days


def current_month_stat() -> dict:
    first_day: str = get_first_months_day()
    users_sum: dict = sum_period_time_costs(first_day)
    return users_sum


def current_week_stat() -> dict:
    first_day: str = get_first_week_day()
    users_sum: dict = sum_period_time_costs(first_day)
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
        result = re.match(r'[a-z]{3,5}-\d{3}([a-z]\d\d)?', long_name)
        short_name = result.group(0)
    return short_name


def projects_report(user: User) -> float:
    time: list = show_week_projects_report(user)
    return sum(time)


def sort_key(day_of_week):
    weekdays: dict = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7
    }
    return weekdays[day_of_week[0]]


def get_list_times() -> list[timedelta, timedelta]:
    return [get_zero_time(), get_zero_time()]


def user_week_data(user: User) -> list[list]:
    first_day: str = get_first_week_day()
    comments: list[Comment] = get_user_costs_per_week(first_day, user)
    week_comments: collections.defaultdict = collections.defaultdict(get_list_times)
    for i in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        week_comments[i] = get_list_times()
    for comment in comments:
        weekday = comment.date.strftime("%A")
        if comment.via_bot:
            week_comments[weekday][0] += comment.time
        week_comments[weekday][1] += comment.time
    coms: list[list] = []
    for i, j in week_comments.items():
        now_comment: list[str, timedelta, timedelta] = [i, j[0], j[1]]
        coms.append(now_comment)
    coms.sort(key=sort_key)
    return coms


def show_month_gist():
    data = current_month_stat()
    users: list[str] = [f"{User.get_user(i).last_name} {User.get_user(i).first_name[0]}." for i in data.keys()]
    time: list[float] = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_time: int = get_count_work_month_days() * 8
    max_value: int = int(max(max(time), max_time)) + 7
    plt.gcf().clear()
    plt.title('Статистика за текущий календарный месяц')

    # plt.axhline(max_value + 10, color='white')
    for i in range(16, max_value, 8):
        if i == max_time:
            continue
        plt.axhline(i, color='grey')
    plt.axhline(8, color='grey', label='День')
    plt.axhline(max_time, color='green', label='Эталон')
    plt.legend(loc=1)
    plt.ylabel('часы')
    step: int = 5 if max_value < 100 else 10
    plt.yticks(np.arange(0, max_value + 8, step=step))
    plt.xticks(rotation=0 if len(users) < 6 else 15)
    plt.bar(users, time)
    plt.savefig('app/db/png/1')


def show_week_gist():
    data = current_week_stat()
    users: list[str] = [f"{user_short_name(i.full_name())}." for i in data.keys()]
    time = [to_float(i) for i in data.values()]
    if len(time) == 0:
        raise EmptyCost
    max_time: int = 5 * 8
    max_value: int = max(max_time, int(max(time))) + 8
    plt.gcf().clear()
    plt.title('Статистика за текущую неделю')
    plt.axhline(max_time, color='green', label='Эталон')
    for i in range(16, max_value, 8):
        if i == max_time:
            continue
        plt.axhline(i, color='grey')
    plt.axhline(8, color='grey', label='День')
    plt.legend(loc=1)
    plt.ylabel('часы')
    plt.yticks(np.arange(0, max_value, step=5))
    plt.xticks(rotation=0 if len(users) < 6 else 15)
    plt.bar(users, time)
    plt.savefig('app/db/png/2')


def show_week_projects_report(user: User):
    data = user_project_week_stat(user)
    projects = list(data.keys())
    # projects = [short_project_name(i) for i in data.keys()]
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
    coms: list = user_week_data(user)
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


async def get_dates() -> list[datetime.date]:
    dates: list[datetime.date] = [date.today()]
    for i in range(1, 8):
        delta = timedelta(days=i)
        dates.append(date.today() - delta)
    return dates


async def sum_costs(now_costs: list[Comment]) -> float:
    sum_s: timedelta = timedelta(0)
    for cost in now_costs:
        sum_s += cost.time
    sum_h: float = sum_s.total_seconds() / 60 / 60
    return sum_h


async def get_data() -> dict[int:dict]:
    users: list[User] = Status.get_users('constructor') + \
                        Status.get_users('electronic') + \
                        Status.get_users('designer') #+ \
                        # Status.get_users('graphics')
    users: list[User] = [user for user in users if user.has_access()]
    users.sort(key=lambda user: user.last_name)

    dates = await get_dates()

    users_costs: dict = {user.full_name(): {date.isoformat(): [] for date in dates} for user in users}
    for user in users:
        costs = [cost for cost in user.comments if cost.date in dates]
        for cost in costs:
            users_costs[user.full_name()][cost.date.isoformat()].append(cost)

    users_summed_costs: dict = {}
    for user in users_costs.keys():
        users_summed_costs[user] = {}
        for date, costs in users_costs[user].items():
            summed_cost = await sum_costs(costs)
            users_summed_costs[user][date] = summed_cost

    return users_summed_costs


async def user_short_name(full_name: str) -> str:
    first, last = full_name.split()
    return f"{last} {first[0]}."


async def get_color(work_day_index, date_index, hours) -> str:
    if int(work_day_index[date_index]) and hours == 0:
        color: str = 'grey'
    elif 7.9 < hours <= 8.1:
        color: str = 'green'
    elif hours == 0:
        color: str = 'darkred'
    elif hours > 8:
        color: str = 'darkgreen'  # 'teal'
    elif 0 < hours <= 1:
        color: str = 'orangered'
    elif 0 < hours <= 2:
        color: str = 'orange'
    elif 2 < hours <= 4:
        color: str = 'yellow'
    elif 4 < hours <= 6:
        color: str = 'greenyellow'
    elif 6 < hours <= 8:
        color: str = 'lime'
    else:
        color: str = 'grey'
    return color


async def create_graf():
    data = await get_data()
    users = list(data.keys())
    dates = await get_dates()
    dates.reverse()
    work_day_index = get_work_day(dates).decode("UTF-8")
    fig, ax = plt.subplots(len(users), len(dates), figsize=(12.85, 8.5))

    for i in range(8):
        ax[0, i].set_title(dates[i])

    for i, user in enumerate(users):
        ax[i, 0].text(-1.9, 0.9, await user_short_name(user))

    for i, axs in enumerate(ax.flat, start=0):
        axs.set_xticklabels([])
        axs.set_yticklabels([])
        axs.set_yticks([])
        axs.set_xticks([])
        date_index = i % 8
        user_index = i // 8
        count_hours = round(data[users[user_index]][dates[date_index].isoformat()], 2)
        axs.text(0.45, 0.9, str(count_hours) + ' часов')
        color_name = await get_color(work_day_index, date_index, count_hours)
        axs.barh(1, 2, height=1, color=color_name)
        axs.set()
        for edge in ['left', 'right', 'bottom', 'top']:
            axs.spines[edge].set_color('#FFFFFF')

    fig.subplots_adjust(left=0.1, right=0.9, top=0.88, bottom=0.08, hspace=0, wspace=0)
    plt.savefig("app/db/png/atata.png")
