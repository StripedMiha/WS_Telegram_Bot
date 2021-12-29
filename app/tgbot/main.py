import datetime
from datetime import timedelta
from pprint import pprint
from typing import Union

from aiogram.utils.exceptions import MessageTextIsEmpty

from app.KeyboardDataClass import KeyboardData
from app.tgbot.auth import TUser
from app.db.db_access import get_user_days_costs, check_comment, get_comment_task_path, remove_comment_db, \
    get_bookmarks_user, \
    remove_users_bookmark_db, get_projects_db, add_project_in_db, get_project_tasks_id_db, add_task_in_db, \
    get_tasks_from_db, get_full_task_name, get_project_id_by_task_id, remove_task_from_db, get_list_user_bookmark, \
    get_all_booked_task_id, add_bookmark_into_db, get_bookmark_id, add_bookmark_to_user, get_tasks_path, \
    add_comment_in_db, change_selected_task, get_all_tasks_id_db, get_all_projects_id_db, \
    get_task_name, get_all_user_day_costs, get_time_notification, get_the_user_costs_for_period
from app.api.ws_api import get_day_costs_from_ws, remove_cost_ws, get_all_project_for_user, search_tasks,\
    get_task_info, add_cost
from app.db.stat import show_month_gist, show_week_gist, sum_period_time_costs

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
    user = TUser(user_id)
    count = len(get_user_days_costs(user))
    if 2 <= count <= 4:
        word = 'записи'
    else:
        word = 'записей'
    return f'Будет удалено {str(count)} {word}.'


def get_users_of_list(selected_list: str) -> list[KeyboardData]:
    all_users = TUser.get_users_list()
    selected_users = [u for u in all_users if u.status == selected_list]
    users: list[TUser] = []
    for i in selected_users:
        users.append(TUser(i.user_id))
    data_for_keyboard: list[KeyboardData] = []
    action = ''
    if selected_list == 'user':
        action: str = 'black_user'
    elif selected_list == 'black':
        action: str = 'known_user'
    for i in users:
        data_for_keyboard.append(KeyboardData(i.full_name, i.user_id, action))
    return data_for_keyboard


def menu_buttons(user: TUser) -> list[list[str]]:
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
                   ['ℹ️ О вас', 'about me'],  # TODO обновить инфу
                   ['💬 Предложение/отзыв', 'offers']]
    return buttons


def about_user(user: TUser) -> str:
    status = 'Администратор' if user.admin else 'Пользователь'
    date = format_date(user.get_date())
    answer = f"Ваше имя - {user.full_name}\n" + \
             f"Ваша почта - {user.get_email()}\n" + \
             f"Ваш статус - {status}\n" + \
             f"Указанная дата - {date}"
    return answer


def see_days_costs(user: TUser) -> str:
    comments = get_user_days_costs(user)
    answer: str = ''
    if comments is None or len(comments) == 0:
        answer = f"Вы не внесли трудоёмкости за {user.get_date()}.\n"\
                 'Не навлекай на себя гнев Ксении. \n'\
                 'Будь умничкой - внеси часы.'
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
        tot_row = f"\nОбщее время за {format_date(user.get_date())}: {format_time(sum_time(total_time))}"
        answer = '\n'.join([answer, tot_row])
    return answer


def days_costs_for_remove(user: TUser) -> list[KeyboardData]:
    comments = get_user_days_costs(user)
    list_comments: list[KeyboardData] = []
    for comment in comments:
        name = ' '.join([format_time(comment[1]), comment[0], comment[2]])
        list_comment = KeyboardData(name, comment[4], "remove_cost_ws")
        list_comments.append(list_comment)
    return list_comments


async def update_day_costs(date: str) -> None:
    db = [i[2] for i in get_all_user_day_costs(date)]
    ws = []
    ws_comments = await get_day_costs_from_ws(date)
    for comment in ws_comments:
        ws.append(int(comment['id']))
        await check_comment(comment)
    for i in ws:
        try:
            db.remove(i)
        except ValueError:
            pass
    for id in db:
        remove_comment_db(id)


def remove_cost(cost_id: int) -> str:
    task_path: str = get_comment_task_path(cost_id)
    req = remove_cost_ws(task_path, cost_id)
    if req.get('status') == 'ok':
        remove_comment_db(cost_id)
        return 'Успешно удалено'
    else:
        return 'Ошибка удаления из WorkSection'


def bookmarks_for_remove(user: TUser) -> list[KeyboardData]:
    bookmarks = get_bookmarks_user(user)
    list_bookmarks: list[KeyboardData] = []
    for bookmark in bookmarks:
        list_bookmarks.append(KeyboardData(bookmark[1], bookmark[0], "remove_bookmark"))
    return list_bookmarks


def remove_bookmark_from_user(id_ub: int) -> None:
    remove_users_bookmark_db(id_ub)


def remove_costs(user: TUser):
    comments = get_user_days_costs(user)
    id_comments = [i[-1] for i in comments]
    for i in id_comments:
        yield remove_cost(i)  # TODO удалить из бд трудоёмкости которые были удалены через сам WS


async def get_project_list(user: TUser) -> list[KeyboardData]:
    projects: list[KeyboardData] = await get_all_project_for_user(user.get_email())
    for i in projects:
        if i.id not in get_projects_db():
            await add_project_in_db(i)
        i.action = "search_task"
    return projects


def update_task_parent(parent_id: int) -> None:
    project_id = get_project_id_by_task_id(str(parent_id))
    project_tasks = search_tasks(f'/project/{project_id}/')
    all_db_task_id = get_project_tasks_id_db(project_id)
    all_ws_task_id: list = []
    for key, value in project_tasks.items():
        all_ws_task_id.append(key)
        if key not in all_db_task_id:
            page = f'/project/{project_id}/{key}/'
            task_info = get_task_info(page)
            add_task_in_db(task_info.get('data'))
        if value.get('child') is not None:
            for sub_key, sub_value in value.get('child').items():
                all_ws_task_id.append(sub_key)
                if sub_key not in all_db_task_id:
                    sub_page = f'/project/{project_id}/{key}/{sub_key}/'
                    subtask_info = get_task_info(sub_page)
                    add_task_in_db(subtask_info.get('data'), key)
    for i in all_db_task_id:
        if i not in all_ws_task_id:
            remove_task_from_db(i)
            # else:
            # print('sub already in base')
        # else:
            # print(value.get('name'))
            # print('already in base')
            # add_task_in_db()
        # if value is not None:
        #     set_parent_task(key, value)


def get_text_add_costs(parent_id: str, user: TUser) -> str:
    name = get_full_task_name(parent_id)
    date = f'Установленная дата - {format_date(user.get_date())}'
    answer: str = '\n'.join([name, date, INPUT_COSTS])
    return answer


def get_tasks(parent_id: str, user_id: int) -> Union[list[KeyboardData], str]:
    user = TUser(user_id)
    child_tasks: list[KeyboardData] = get_tasks_from_db(parent_id)
    if parent_id in get_all_projects_id_db():
        update_task_parent(int(parent_id))
    if len(child_tasks) == 0:
        return get_text_add_costs(parent_id, user)
    for i in child_tasks:
        i.action = "search_task"
    if parent_id not in get_all_projects_id_db():
        child_tasks.reverse()
        task_name = ' '.join([f'🗂', get_task_name(parent_id)])
        child_tasks.append(KeyboardData(task_name, int(parent_id), 'input_here'))
        child_tasks.reverse()
    return child_tasks


def get_list_bookmark(user_id: int) -> Union[list[KeyboardData], str]:
    user_list_bookmark: list[KeyboardData] = get_list_user_bookmark(user_id)
    if len(user_list_bookmark) == 0:
        return 'У вас нет закладок.\n Добавить закладки можно через кнопку "Найти задачу"'
    for i in user_list_bookmark:
        i.action = "search_task"
    return user_list_bookmark  # TODO две подобные функции выдающие закладки


def add_costs(message: str, data: dict) -> str:
    user = TUser(data.get('user_id'))
    date = user.get_date()
    email = user.get_email()
    path = get_tasks_path(data.get('id'))
    list_comments: list[list[str, timedelta]] = parse_input_comments(message)
    for comments_text, comments_time in list_comments:
        req = add_cost(page=path,
                       user_email=email,
                       comment=comments_text,
                       time=comments_time,
                       date=date)
        status = req.get('status')
        if status == 'ok':
            comment_id = req.get('id')
            add_comment_in_db(comment_id, user.user_id, data.get('id'), comments_time, comments_text, date)
            yield 'Успешно внесено'
        else:
            yield 'Не внесено'


def to_correct_time(time: str) -> datetime.timedelta:
    out_time: datetime.timedelta
    if ':' in time:
        out_time = timedelta(hours=int(time.split(':')[0]),
                             minutes=int(time.split(':')[1]))
    else:
        time = float(time.replace(',', '.') if ',' in time else time)
        out_time = timedelta(hours=time)
    return out_time


def time_to_comment(comments: list[str], time_d: datetime.timedelta):
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
    if task_id in get_all_booked_task_id():
        return "Такая закладка уже есть. Отмена"
    else:
        add_bookmark_into_db(task_id)
        bookmark_id = get_bookmark_id(task_id)
        add_bookmark_to_user(user_id, bookmark_id)
        return "Закладка добавлена"

    
def get_month_stat():
    show_month_gist()


def get_week_stat():
    show_week_gist()


def select_task(user_id: int, task_ws_id) -> str:
    change_selected_task(user_id, task_ws_id)
    return '\n'.join(['Выбранная задача:', get_full_task_name(task_ws_id)])


def check_task_id(text: str) -> bool:
    tasks_id = get_all_tasks_id_db()
    if text in tasks_id:
        return True
    else:
        return False


async def get_time_user_notification():
    times = await get_time_notification()
    return times


async def day_report_message(user: TUser) -> str:
    now_time: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    now_date: str = datetime.datetime.now().strftime("%Y-%m-%d")
    costs: list = get_the_user_costs_for_period(user, now_date)
    day_cost_sum: timedelta = timedelta(hours=0)
    for i in costs:
        hours, minutes = i.split(":")
        day_cost_sum += timedelta(hours=int(hours), minutes=int(minutes))
    day_cost_sum: float = day_cost_sum.seconds / 60 / 60
    text: str = ' '
    if user.notification_status:
        if user.get_notification_time() == now_time:
            if day_cost_sum >= 12:
                text = "\n\n".join(["Вы либо очень большой молодец, либо где-то переусердствовали."
                                    "\nУ вас за сегодня больше 12 часов. Это законно?", see_days_costs(user)])
            elif day_cost_sum >= 8:
                text = "\n\n".join(["Вы всё заполнили, вы молодец!", see_days_costs(user)])
            elif day_cost_sum > 0:
                text = "\n\n".join(["Вы немного не дотянули до 8 часов!", see_days_costs(user)])
            else:
                text = see_days_costs(user)
        elif user.get_remind_notification_time() == now_time:
            text = "Вы отложили напоминание заполнить трудоёмкости. Вот оно!"
            user.set_remind_time(None)
    return text


async def set_remind(user: TUser, time: str, message_time: datetime.datetime) -> str:
    hours, minutes = time.split(".")
    remind_time: datetime.timedelta = datetime.timedelta(hours=int(hours), minutes=int(minutes))
    user.set_remind_time(message_time + remind_time)
    return "Напоминание будет в %s" % user.remind_notification.strftime("%H:%M")


if __name__ == '__main__':
    pass
