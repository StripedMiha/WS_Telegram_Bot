# import datetime
import logging
from datetime import datetime, timedelta
from pprint import pprint
from typing import Union

from app.KeyboardDataClass import KeyboardData
from app.api.work_calendar import is_work_day
from app.create_log import setup_logger
from app.db.structure_of_db import User, Comment, Bookmark, Task, Project, Status
from app.exceptions import NotUserTime, EmptyDayCosts
from app.db.db_access import get_user_days_costs, check_comments, get_all_user_day_costs, get_the_user_costs_for_period
from app.api.ws_api import get_day_costs_from_ws, remove_cost_ws, get_all_project_for_user, search_tasks, \
    get_task_info, add_cost, get_the_cost_for_check
from app.db.stat import show_month_gist, show_week_gist, get_first_week_day, show_week_report

main_logger: logging.Logger = setup_logger("App.back.main", "app/log/main.log")
back_logger: logging.Logger = setup_logger("App.back", "app/log/back.log")

INPUT_COSTS = """
Введите часы и описание деятельности:
Можно ввести в одну строку, можно в несколько(но в одном сообщении).
В начале указываете количество часов, следом через '!' можно перечислить один или несколько комментариев.
Можно ввести больше двух часов. Алгоритм сам разделит по два часа. Пробелы между '!' не важны

Пример№1:\n<i>3</i> ! <i>Печать деталей корпуса</i> ! <i>Сборка печатного прототипа</i>
"""

# Для выбора задачи для быстрого ввода введите '<i>выбрать</i>'
# Для отмены введите '<i>отмена</i>'
# Для более подробного описания введите '<i>Ничего не понял</i>'
# Для добавления задачи в закладки введите '<i>Добавить закладку</i>'

# "\n\n"
# "Пример№2:\n<i>0.5</i>! <i>Печать деталей корпуса</i> \n"
# "<i>2.5</i>! <i>Сборка печатного прототипа</i>\n\n"
# "В первом примере в бот разделит указанное количество часов на количество задач,"
# "в данном случае в WS улетит две записи по полтора часа.\n"
# "Во втором примере в WS улетит 3 записи:\n"
# "Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся"
# "на две записи: на запись с двумя часами и запись с получасом."
# """


INPUT_COST_EXAMPLE = """
Дробную и целую часть часа можно разделить '.', ','
Если использовать ':', то будет взято точно указанное количество минут
Пример№1:
<i>3</i> ! <i>Печать деталей корпуса</i> ! <i>Сборка печатного прототипа</i>

Пример№2:
<i>0.5</i>! <i>Печать деталей корпуса</i>
<i>2.5</i>! <i>Сборка печатного прототипа</i>

В первом примере в бот разделит указанное количество часов на количество задач, 
в данном случае в WS улетит две записи по полтора часа.

Во втором примере в WS улетит 3 записи:
Полчаса по первому комментарию. А по второму комментарию 2,5 часа разделятся на две записи: 
на запись с двумя часами и запись с получасом.
"""
remind_settings_button: list = [["Вкл/выкл напоминания", "toggle_notifications"],
                                ["Установить время для напоминаний", "Set_notification_time"]]


def format_time(time: str) -> str:
    hours = int(time.split(':')[0].strip(' '))
    minutes = int(time.split(':')[1].strip(' '))
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


def format_date(date: str) -> str:
    f_date = 'сегодня' if date == 'today' else date
    return f_date


def sum_time(times: list[str]) -> str:
    tot_time: timedelta = timedelta()
    for i in times:
        tot_time += timedelta(hours=int(i.split(':')[0]), minutes=int(i.split(':')[1]))
    return ':'.join(str(tot_time).split(':')[:2])


def text_count_removed_costs(user_id: int) -> str:
    user = User.get_user(user_id)
    count = len(get_user_days_costs(user.user_id, user.get_date()))
    if 2 <= count <= 4:
        word = 'записи'
    else:
        word = 'записей'
    return f'Будет удалено {str(count)} {word}.'


def get_users_of_list(selected_list: str) -> list[KeyboardData]:
    users: list[User] = Status.get_users(selected_list)
    data_for_keyboard: list[KeyboardData] = []
    action_dict: dict = {"user": "black_user",
                         "black": "known_user",
                         "admin": ''}
    for i in users:
        data_for_keyboard.append(KeyboardData(i.full_name(), i.user_id, action_dict[selected_list]))
    return data_for_keyboard


def menu_buttons(user: User) -> list[list[str]]:
    if user.get_email() is None:
        buttons = [['Обо мне', 'about me'],
                   ['Установить почту', 'set email']]
    else:
        buttons = [[f"📃 Отчёт за {format_date(user.get_date())}", 'daily report'],
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
    status = 'Администратор' if user.is_admin() else 'Пользователь'
    date = format_date(user.get_date())
    notif_status = "включены" if user.notification_status else "выключены"
    answer = [f"Ваше имя - {user.full_name()}",
              f"Ваша почта - {user.get_email()}",
              f"Ваш статус - {status}",
              f"Указанная дата - {date}",
              f"Задача по умолчанию - {user.default_task.full_name()}",
              f"Статус напоминаний - {notif_status}",
              f"Время напоминаний - {user.get_notification_time()}"]
    return "\n".join(answer)


def get_text_for_empty_costs(date: str) -> str:
    return f"Вы не внесли трудоёмкости за {date}.\n" \
           "Не навлекай на себя гнев Ксении. \n" \
           "Будь умничкой - внеси часы."


async def see_days_costs(user: User, date: str = "0") -> str:
    if date != "0" and date != user.get_date():
        await update_day_costs(date, True)
    else:
        date = user.get_date()
    comments = get_user_days_costs(user.user_id, date)
    answer: str = ''
    if comments is None or len(comments) == 0:
        answer = get_text_for_empty_costs(date)
    else:
        total_time: list[str] = []
        prev_proj_name, prev_task_name = comments[0][3], comments[0][2]
        now_proj = ' '.join(["Проект:", prev_proj_name])
        now_task = ' '.join(["  Задача:", prev_task_name])
        now_row = ' '.join(["    Потрачено:", format_time(comments[0][1]), "на", comments[0][0]])
        answer = "\n".join([now_proj, now_task, now_row])
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
        tot_row = f"\nОбщее время за {format_date(date)}: {format_time(sum_time(total_time))}"
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


async def update_day_costs(date: str, one_day: bool = False) -> None:
    main_logger.info('start update day cost')
    db = [i[2] for i in await get_all_user_day_costs(date)]
    ws_comments = await get_day_costs_from_ws(date, one_day)
    ws = [int(comment['id']) for comment in ws_comments]
    await check_comments(ws_comments)
    db_for_remove = [Comment.get_comment(i) for i in list(set(db) - set(ws))]
    for comment in db_for_remove:
        comment.remove()
    main_logger.info('end update day cost')


def remove_cost(cost_id: int) -> str:
    comment = Comment.get_comment(cost_id)
    req = remove_cost_ws(comment.task.task_path, comment.comment_id)
    if req.get('status') == 'ok':
        comment.remove()
        return 'Успешно удалено'
    else:
        return 'Ошибка удаления из WorkSection'


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
        yield remove_cost(i)  # TODO удалить из бд трудоёмкости которые были удалены через сам WS


async def get_project_list(user: User) -> list[KeyboardData]:
    projects: list[KeyboardData] = await get_all_project_for_user(user.get_email())
    projects_id: set[int] = Project.get_all_projects_id_from_db()  # get_projects_db()
    for i in projects:
        if i.id not in projects_id:
            Project.new_project(i)
        i.action = "search_task"
    return projects


def update_task_parent(parent_id: str) -> None:
    project: Project = Project.get_project(str(parent_id))
    project_tasks = search_tasks(f'/project/{project.project_id}/')
    all_db_task_id: set = {task.task_ws_id for task in project.tasks}
    all_ws_task_id: set = set()
    for key, value in project_tasks.items():
        all_ws_task_id.add(key)
        task: Task = Task.get_task_via_ws_id(key)
        if key not in all_db_task_id:
            page = f'/project/{project.project_id}/{key}/'
            task_info = get_task_info(page)
            Task.new_task(task_info.get('data'))
        elif task.parent_id != value.get("parent") or isinstance(task.parent_id, type(None)):
            task.update(value.get("parent"))
        if value.get('child') is not None:
            for sub_key, sub_value in value.get('child').items():
                all_ws_task_id.add(sub_key)
                sub_task: Task = Task.get_task_via_ws_id(sub_key)
                if sub_key not in all_db_task_id:
                    sub_page = f'/project/{project.project_id}/{key}/{sub_key}/'
                    subtask_info = get_task_info(sub_page)
                    Task.new_task(subtask_info.get('data'), key)
                elif Task.get_task_via_ws_id(sub_key).parent_id != sub_value.get("parent"):
                    sub_task.update(sub_value.get("parent"))
    # Пометить удалёнными в дб задачи, которые были удалены из ws
    for i in all_db_task_id - all_ws_task_id:
        Task.get_task_via_ws_id(i).mark_remove()


def get_text_add_costs(task_id: str, user: User) -> str:
    task = Task.get_task_via_ws_id(task_id)
    date = f'Установленная дата - {format_date(user.get_date())}'
    answer: str = '\n'.join([task.full_name(), date, INPUT_COSTS])
    return answer


def get_tasks(parent_id: str, user_id: int) -> Union[list[KeyboardData], str]:
    user = User.get_user(user_id)
    projects_id: set[int] = Project.get_all_projects_id_from_db()
    if parent_id in projects_id:
        update_task_parent(parent_id)
    subtasks: list[Task] = Task.get_subtasks(parent_id)

    if len(subtasks) == 0:
        return get_text_add_costs(parent_id, user)
    else:
        child_tasks: list[KeyboardData] = []
        if parent_id not in projects_id:
            task_name = ' '.join([f'🗂', Task.get_task_via_ws_id(parent_id).task_name])
            child_tasks += [KeyboardData(task_name, int(parent_id), 'input_here')]
        child_tasks += [KeyboardData(task.task_name, task.task_ws_id, "search_task")
                        for task in subtasks]

        # child_tasks.reverse()
        # task_name = ' '.join([f'🗂', Task.get_task_via_ws_id(parent_id).task_name])
        # child_tasks.append(KeyboardData(task_name, int(parent_id), 'input_here'))
        # child_tasks.reverse()
    return child_tasks


def get_list_bookmark(user_id: int) -> Union[list[KeyboardData], str]:
    user: User = User.get_user(user_id)
    user_list_bookmark: list[KeyboardData] = [KeyboardData(bookmark.bookmark_name, bookmark.task.task_ws_id)
                                              for bookmark in user.bookmarks]
    # user_list_bookmark: list[KeyboardData] = get_list_user_bookmark(user_id)
    if len(user_list_bookmark) == 0:
        return 'У вас нет закладок.\n Добавить закладки можно через кнопку "Найти задачу"'
    for i in user_list_bookmark:
        i.action = "search_task"
    return user_list_bookmark  # TODO две подобные функции выдающие закладки


def add_costs(message: str, data: dict) -> str:
    user: User = User.get_user(data.get('user_id'))
    date: str = user.get_date()
    email: str = user.get_email()
    path: str = Task.get_task_via_ws_id(data.get('id')).task_path
    list_comments: list[list[str, timedelta]] = parse_input_comments(message)
    for comments_text, comments_time in list_comments:
        req = add_cost(page=path,
                       user_email=email,
                       comment=comments_text,
                       time=comments_time,
                       date=date)
        status = req.get('status')
        pprint(req)
        if status == 'ok':
            comment_id = req.get('id')
            f_date = datetime.now().strftime("%d.%m.%Y") if date == 'today' else date
            check_data = [comment_id, path, email, comments_text, comments_time, f_date]
            check = check_adding(check_data)
            if check:
                task_db_id: int = Task.get_task_via_ws_id(data.get('id')).task_id
                Comment.add_comment_in_db(int(comment_id), user.user_id, task_db_id, comments_time, comments_text, date)
                yield 'Успешно внесено'
            else:
                yield 'Ошибка проверки внесения'
        else:
            yield 'Не внесено'


def check_adding(data: list):
    comment_id, path, email, comment_text, comment_time, date = data
    req: dict = get_the_cost_for_check(date, path)
    if req.get("status") == "ok":
        costs = req.get("data")
        the_cost = {}
        for cost in costs:
            if int(cost.get("id")) == comment_id:
                the_cost = cost
                break
        if the_cost.get("comment") != comment_text \
                or the_cost.get("task").get("page") != path \
                or the_cost.get("user_from").get("email") != email \
                or the_cost.get("comment") != comment_text \
                or datetime.strptime(the_cost.get("date"), "%Y-%m-%d").strftime("%d.%m.%Y") != date:
            return False
        return True
    return False


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


def add_bookmark(user_id: int, task_id: str) -> str:
    user: User = User.get_user(user_id)
    if task_id in [bookmark.task.task_ws_id for bookmark in user.bookmarks]:
        return "Такая закладка уже есть. Отмена"
    else:
        bookmark: Bookmark = Bookmark.get_bookmark(int(task_id))
        user.add_bookmark(bookmark)
        return "Закладка добавлена"


def get_month_stat():
    show_month_gist()


def get_week_stat():
    show_week_gist()


async def get_week_report_gist(user: User):
    first_week_day = get_first_week_day()
    await update_day_costs(first_week_day)
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
    text: str = ' '
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
    return text, day_cost_hours


if __name__ == '__main__':
    pass
