import logging
import re
from datetime import datetime, timedelta
from typing import Union, List

from sqlalchemy.exc import NoResultFound

from app.KeyboardDataClass import KeyboardData
from app.api.work_calendar import is_work_day
from app.create_log import setup_logger
from app.db.structure_of_db import User, Comment, Bookmark, Task, Status
from app.exceptions import NotUserTime, EmptyDayCosts, CancelInput, WrongDate, FutureDate
from app.db.db_access import get_user_days_costs, get_the_user_costs_for_period
from app.back.stat import show_month_gist, show_week_gist, get_first_week_day, show_week_report

main_logger: logging.Logger = setup_logger("App.back.main", "app/log/main.log")
back_logger: logging.Logger = setup_logger("App.back", "app/log/back.log")


INPUT_COST_EXAMPLE = """
Дробную и целую часть часа можно разделить '.', ','
Если использовать ':', то будет взято точно указанное количество минут
Пример№1:
<i>3</i> ! <i>Печать деталей корпуса</i> ! <i>Сборка печатного прототипа</i>

Пример№2:
<i>0.5</i>! <i>Печать деталей корпуса</i>
<i>2.5</i>! <i>Сборка печатного прототипа</i>

В первом примере в бот разделит указанное количество часов на количество задач, 
в данном случае добавится две записи по полтора часа.

Во втором примере добавится 3 записи:
Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся на две записи: 
на запись с двумя часами и запись с получасом.
"""
remind_settings_button: list = [["Вкл/выкл напоминания", "toggle_notifications"],
                                ["Установить время для напоминаний", "Set_notification_time"]]


def format_time(time: timedelta) -> str:
    hours = time.seconds // 60 // 60
    minutes = time.seconds // 60 % 60
    f_hours: str = ''
    f_minutes: str = ''
    if minutes > 0:
        f_minutes = f'{minutes} минут'
    if hours >= 0:
        if hours == 1:
            word = 'час'
        elif 2 <= hours <= 4:
            word = 'часа'
        elif hours == 0:
            return f_minutes
        else:
            word = 'часов'
        f_hours = f'{hours} {word}'
    return ' '.join([f_hours, f_minutes])


def to_ru_today_date(date: str) -> str:
    f_date = 'сегодня' if date == 'today' else date
    return f_date


def sum_time(times: list[timedelta]) -> timedelta:
    tot_time: timedelta = timedelta()
    for i in times:
        tot_time += i
    return tot_time


def text_count_removed_costs(user_id: int) -> str:
    user = User.get_user_by_telegram_id(user_id)
    count: int = len(get_user_days_costs(user.user_id, user.get_date()))
    if 2 <= count <= 4:
        word = 'записи'
    else:
        word = 'записей'
    return f'Будет удалено {str(count)} {word}.'


def get_users_of_list(selected_list: str) -> list[KeyboardData]:
    users: list[User] = Status.get_users(selected_list)
    data_for_keyboard: list[KeyboardData] = []
    action_dict: dict = {"user": "blocked_user",
                         "blocked": "known_user",
                         "admin": ''}
    for i in users:
        data_for_keyboard.append(KeyboardData(i.full_name(), i.user_id, action_dict[selected_list]))
    data_for_keyboard.sort(key=lambda i: i.text)
    return data_for_keyboard


async def check_user(telegram_id: int) -> Union[User, list]:
    try:
        user: User = User.get_user_by_telegram_id(telegram_id)
        return user
    except NoResultFound:
        return [("Я новый пользователь", "new_user"),
                ("Пользовался WorkSection", "old_user")]


def menu_buttons(user: User) -> list[list[str]]:
    if user.get_email() is None:
        buttons = [['Обо мне', 'about me'],
                   ['Установить почту', 'set email']]
    else:
        buttons = [[f"📃 Отчёт за {user.get_date(True)}", 'daily report'],
                   ['🔍 Найти задачу', 'get tasks list'],
                   ['❌🕓 Удалить трудоёмкость', 'remove time cost'],
                   ['❌🧷 Удалить закладку', 'remove book'],
                   ['🔄📅 Изменить дату', 'change date'],
                   ['🔄📧 Изменить почту', 'change email'],
                   ['⏰ Настройки оповещений', 'notifications'],
                   ['ℹ️ О вас', 'about me'],
                   ['💬 Предложение/отзыв', 'offers']]
    return buttons


def get_about_user_info(user: User) -> str:
    answer = [f"Ваше имя - {user.full_name()}",
              f"Ваша почта - {user.get_email()}",
              f"Ваш статус - {', '.join([status.status_ru_name for status in user.statuses])}",
              f"Указанная дата - {user.get_date(True)}",
              f"Задача по умолчанию - {user.default_task.full_name() if user.default_task else 'не установлена'}",
              f"Статус напоминаний - {'включены' if user.notification_status else 'выключены'}",
              f"Время напоминаний - {user.get_notification_time()}"]
    return "\n".join(answer)


def get_text_for_empty_costs(date: str) -> str:
    return f"Вы не внесли трудоёмкости за {date}.\n" \
           "Не навлекай на себя гнев Ксении. \n" \
           "Будь умничкой - внеси часы."


async def see_days_costs(user: User, date: str = "0") -> str:
    if date == "0":
        date = user.get_date()
    comments: list[tuple[str, timedelta, str, str, int]] = get_user_days_costs(user.user_id, date)
    answer: str = ''
    if comments is None or len(comments) == 0:
        answer: str = get_text_for_empty_costs(date)
    else:
        total_time: list[timedelta] = []
        prev_proj_name, prev_task_name = comments[0][3], comments[0][2]
        now_proj = ' '.join(["Проект:", prev_proj_name])
        now_task = ' '.join(["  Задача:", prev_task_name])
        now_row = ' '.join(["    Потрачено:", format_time(comments[0][1]), "на", comments[0][0]])
        answer: str = "\n".join([now_proj, now_task, now_row])
        total_time.append(comments[0][1])
        for comment in comments[1:]:
            cur_proj_name, cur_task_name = comment[3], comment[2]
            cur_time, cur_text = comment[1], comment[0]
            if prev_proj_name == cur_proj_name:
                if prev_task_name == cur_task_name:
                    now_row = ' '.join(['    Потрачено:', format_time(cur_time), 'на', cur_text])
                    answer = '\n'.join([answer, now_row])
                else:
                    prev_task_name = cur_task_name
                    now_task = ' '.join(["  Задача:", cur_task_name])
                    now_row = ' '.join(['    Потрачено:', format_time(cur_time), 'на', cur_text])
                    answer = '\n'.join([answer, now_task, now_row])
            else:
                now_proj = ' '.join(["\nПроект:", cur_proj_name])
                now_task = ' '.join(["  Задача:", cur_task_name])
                now_row = ' '.join(['    Потрачено:', format_time(cur_time), 'на', cur_text])
                answer = '\n'.join([answer, now_proj, now_task, now_row])
                prev_task_name = cur_task_name
                prev_proj_name = cur_proj_name
            total_time.append(cur_time)
        tot_row = f"\nОбщее время за {to_ru_today_date(date)}: {format_time(sum_time(total_time))}"
        answer = '\n'.join([answer, tot_row])
    return answer


def days_costs_for_remove(user: User) -> list[KeyboardData]:
    comments = get_user_days_costs(user.user_id, user.get_date())
    list_comments: list[KeyboardData] = []
    for comment in comments:
        name = ' '.join([format_time(comment[1]), comment[0], comment[2]])
        list_comment = KeyboardData(name, comment[4], "remove_cost_ws")
        list_comments.append(list_comment)
    return list_comments


def remove_cost(cost_id: int) -> str:
    comment = Comment.get_comment(cost_id)
    try:
        comment.remove()
        return 'Успешно удалено'
    except Exception as e:
        return 'Ошибка удаления'


def bookmarks_for_remove(user: User) -> list[KeyboardData]:
    bookmarks = user.bookmarks  # get_bookmarks_user(user)
    list_bookmarks: list[KeyboardData] = []
    for bookmark in bookmarks:
        list_bookmarks.append(KeyboardData(bookmark.bookmark_name, bookmark.bookmark_id, "remove_bookmark"))
    return list_bookmarks


def remove_costs(user: User):
    comments = get_user_days_costs(user.user_id, user.get_date())
    id_comments = [i[-1] for i in comments]
    for i in id_comments:
        yield remove_cost(i)


async def create_task(name: str, data: dict):
    project_id = data.get("project_id")
    task_id = data.get("task_id")
    if task_id:
        project_id = Task.get_task(task_id).project_id
    Task.new_task(name, project_id, task_id)


def get_list_bookmark(user_id: int) -> Union[list[KeyboardData], str]:
    user: User = User.get_user_by_telegram_id(user_id)
    user_list_bookmark: list[KeyboardData] = [KeyboardData(bookmark.bookmark_name, bookmark.task.task_id)
                                              for bookmark in user.bookmarks]
    if len(user_list_bookmark) == 0:
        return 'У вас нет закладок.\n Добавить закладки можно через кнопку "Найти задачу"'
    for i in user_list_bookmark:
        i.action = "input_here"
    return user_list_bookmark  # TODO две подобные функции выдающие закладки


def add_costs(message: str, data: dict) -> str:
    user: User = User.get_user_by_telegram_id(data.get('user_id'))
    date: str = user.get_date()
    email: str = user.get_email()
    task_id: int = data.get('id')
    list_comments: list[list[str, timedelta]] = parse_input_comments(message)
    for comments_text, comments_time in list_comments:
        f_date = datetime.now().strftime("%d.%m.%Y") if date == 'today' else date
        try:
            print(comments_time, date)
            Comment.add_comment_in_db(user.user_id, task_id, comments_time, comments_text, date)
            yield 'Успешно внесено'
        except Exception as e:
            yield 'Не внесено'


async def reactivate_task_keyboard(task_id: int) -> List[KeyboardData]:
    """
    возвращает набор данных для реактивации задачи
    :param task_id:
    :return:
    """
    buttons: List[KeyboardData] = [KeyboardData("Активировать задачу", task_id, "reactivate_task"),
                                   KeyboardData("Оставить выполненной", task_id, "keep_completed")]
    return buttons


async def task_fate(user: User, task: Task, action: str) -> tuple[str, str]:
    """
    Подготовка сообщений для пользователя и менеджеров после реактивации(или нет) задачи
    :param user:
    :param task:
    :param action:
    :return:
    """
    to_user: str = ""
    to_manager: str = ""
    if action == "reactivate_task":
        task.reactivate_task()
        to_user = f"Задача {task.task_name} вновь активна"
        to_manager = f"Пользователь {user.full_name()} внёс трудозатраты в неактивную задачу " \
                     f"{task.task_name} и реактивировал её"
    if action == "keep_completed":
        to_user = f"Задача {task.task_name} осталась неактивной"
        to_manager = f"Пользователь {user.full_name()} внёс трудозатраты в неактивную задачу " \
                     f"{task.task_name} и не активировал её"
    return to_user, to_manager


def to_correct_time(time: str) -> timedelta:
    out_time: timedelta
    if ':' in time:
        out_time = timedelta(hours=int(time.split(':')[0]),
                             minutes=int(time.split(':')[1]))
    else:
        time = float(time.replace(',', '.') if ',' in time else time)
        out_time = timedelta(hours=time)
    return out_time


def time_to_comment(comments: list[str], time_d: timedelta):
    max_time_cost = timedelta(hours=2)
    for comment in comments:
        comment_time = time_d / len(comments)
        if comment_time > max_time_cost:
            split_comment_time = comment_time
            while split_comment_time > max_time_cost:
                split_comment_time -= max_time_cost
                yield [comment, max_time_cost]
            yield [comment, split_comment_time]
        else:
            yield [comment, comment_time]


def parse_input_comments(message: str) -> list[list[str, timedelta]]:
    list_rows: list = message.split('\n')
    comment_with_time: list[list[str, timedelta]] = list(list())
    for row in list_rows:
        comments = [i.strip(' ') for i in row.split('!')[1:]]
        if '' in comments:
            comments.remove('')
        time_d = to_correct_time(row.split('!')[0])
        for i in time_to_comment(comments, time_d):
            comment_with_time.append(i)
    for i in comment_with_time:
        i[1] = ':'.join(str(i[1]).split(':')[:2])
    return comment_with_time


def add_bookmark(user_id: int, task_id: int) -> str:
    user: User = User.get_user(user_id)
    if task_id in [bookmark.task.task_id for bookmark in user.bookmarks]:
        return "Такая закладка уже есть. Отмена добавления."
    else:
        bookmark: Bookmark = Bookmark.get_bookmark(task_id)
        user.add_bookmark(bookmark)
        return "Закладка добавлена"


def get_month_stat():
    show_month_gist()


def get_week_stat():
    show_week_gist()


async def get_week_report_gist(user: User) -> None:
    first_week_day = get_first_week_day()
    show_week_report(user)


def get_text_menu_notification(status: bool) -> str:
    answer: str = "Настройки напоминаний"
    st = "Сейчас напоминания %s" % ("включены 🔔" if status else "выключены 🔕")
    return "\n".join([answer, st])


async def set_remind(user: User, time: str, message_time: datetime) -> str:
    hours, minutes = time.split(".")
    remind_time: timedelta = timedelta(hours=int(hours), minutes=int(minutes))
    user.set_remind_time(message_time + remind_time)
    return "Напоминание будет в %s" % user.remind_notification.strftime("%H:%M")


DATE_PATTERN = r'(0[1-9]|[1-2][0-9]|3[0-1])[., :](0[1-9]|1[0-2])[., :](20[2-9][0-9])'


async def change_date(user: User, new_date: str) -> str:
    if any([i == new_date for i in ("отмена", "cancel")]):
        raise CancelInput
    elif any([i == new_date for i in ("сегодня", "today")]):
        user.change_date(new_date)
        return "Теперь бот будет записывать на текущий день"
    elif any([i == new_date for i in ("вчера", "yesterday")]):
        new_date = (datetime.today() - timedelta(days=1)).strftime("%d.%m.%Y")
        user.change_date(new_date)
        return "Установлена вчерашняя дата"
    elif re.match(DATE_PATTERN, new_date):
        date = re.match(DATE_PATTERN, new_date)
        format_date = f"{date.group(1)}.{date.group(2)}.{date.group(3)}"
        if datetime(year=int(date.group(3)), month=int(date.group(2)), day=int(date.group(1))) > datetime.now():
            raise FutureDate
        user.change_date(format_date)
        return f'Установлена дата: {user.get_date(True)}'
    else:
        raise WrongDate


DATE_BUTTONS = ["Вчера", "Сегодня", "Отмена"]


async def fast_date_keyboard(user: User) -> list[str]:
    if user.get_date() == "today":
        return DATE_BUTTONS
    else:
        now = datetime.strptime(user.get_date(), "%d.%m.%Y")
        one = timedelta(days=1)
        ans: list[str] = [(now - one).strftime("%d.%m.%Y"), (now + one).strftime("%d.%m.%Y")] + DATE_BUTTONS
        return ans


def get_rus_weekday(eng_weekday: str) -> str:
    rus_weekday = {
        "Monday": "понедельник",
        "Tuesday": "вторник",
        "Wednesday": "среду",
        "Thursday": "четверг",
        "Friday": "пятницу",
        "Saturday": "субботу",
        "Sunday": "воскресенье",
    }
    return rus_weekday[eng_weekday]


def get_header_for_report(hours: float, date: str) -> str:
    datetime_date = datetime.strptime(date, '%Y-%m-%d')
    date_for_header = " ".join([get_rus_weekday(datetime_date.strftime('%A')), datetime_date.strftime('%d.%m.%Y')])
    date_header = f"Отчёт за {date_for_header}."
    header: str = ''
    if hours >= 12:
        header: str = "Вы либо очень большой молодец, либо где-то переусердствовали." \
                      "\nУ вас за сегодня больше 12 часов. Это законно?"
    elif hours >= 8:
        header: str = "Вы всё заполнили, вы молодец!"
    elif hours > 0:
        header: str = "Вы немного не дотянули до 8 часов!"
    return "\n".join([date_header, header])


def sum_costs_to_float(costs: list[str]) -> float:
    day_cost_hours: timedelta = timedelta(hours=0)
    for i in costs:
        hours, minutes = i.split(":")
        day_cost_hours += timedelta(hours=int(hours), minutes=int(minutes))
    day_cost_hours: float = day_cost_hours.seconds / 60 / 60 + (day_cost_hours.days * 24)
    return day_cost_hours


def get_work_date_for_report(notification_time) -> str:
    if datetime.strptime(notification_time, "%H:%M").time().hour < 13:
        i = 1
        while not is_work_day(datetime.now() - timedelta(days=i)):
            i += 1
        now_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
    else:
        now_date: str = datetime.now().strftime("%Y-%m-%d")
    return now_date


async def day_report_message(user: User) -> tuple[str, float]:
    now_time: str = datetime.now().strftime("%H:%M")
    # text: str = ' '
    day_cost_hours: float = 0.0
    if user.notification_status:
        notif_time = user.get_notification_time().split(" ")[1]
        if notif_time == now_time:
            now_date: str = get_work_date_for_report(notif_time)
            main_logger.info("Подготавливаем для %s ежедневный отчёт/напоминание" % user.full_name())
            costs: list = get_the_user_costs_for_period(user, now_date)
            day_cost_hours: float = sum_costs_to_float(costs)
            main_logger.info("Пользователь %s наработал на %s часов" % (user.full_name(), day_cost_hours))
            text = "\n\n".join([get_header_for_report(day_cost_hours, now_date), await see_days_costs(user, now_date)])
        elif user.get_remind_notification_time() == now_time:
            main_logger.info("Пользователь %s откладывал напоминание. Присылаем." % user.full_name())
            text = "Вы отложили напоминание заполнить трудоёмкости. Вот оно!"
            user.set_remind_time(None)
        else:
            raise NotUserTime
        if day_cost_hours <= 0:
            raise EmptyDayCosts
    else:
        raise NotUserTime  # Не надо отправлять
    return text, day_cost_hours


if __name__ == '__main__':
    pass
