# from typing import Union

# from app.api.ws_api import get_day_costs_from_ws
from datetime import datetime

from sqlalchemy import select

from app.KeyboardDataClass import KeyboardData
from app.db.structure_of_db import Comment, Project, Task, User, Bookmark, UserBookmark
from app.tgbot.auth import _get_session, TUser


def get_user_days_costs(user: TUser) -> list[tuple]:
    session = _get_session()
    query_comments = session.query(Comment.comment_text, Comment.time, Task.task_name, Project.project_name,
                                   Comment.comment_id) \
        .join(Comment).join(Project) \
        .filter(Comment.user_id == user.user_id,
                Comment.date == user.get_date()).order_by(Project.project_name, Task.task_name).all()
    session.close()
    return query_comments


def get_all_user_day_costs(date: str) -> list[tuple]:
    session = _get_session()
    all_comments = session.query(Comment.comment_text, Comment.time, Comment.comment_id) \
        .filter(Comment.date == date).all()
    session.close()
    return all_comments


def get_all_costs_for_period(first_day: str):
    session = _get_session()
    q = session.query(Comment.user_id, Comment.time) \
        .filter(Comment.date >= first_day, Comment.via_bot == True).all()
    session.close()
    return [list(i) for i in q]


def get_the_user_costs_for_period(user: TUser, day_from: str) -> list:
    session = _get_session()
    q = session.query(Comment.time).filter(Comment.user_id == user.user_id, Comment.date >= day_from).all()
    session.close()
    return [i[0] for i in q]


def get_period_user(first_day: str) -> list[int]:
    session = _get_session()
    users: list[tuple[int, str]] = session.query(Comment.user_id) \
        .filter(Comment.date >= first_day, Comment.via_bot == True).all()
    session.close()
    return [i[0] for i in users]


def get_the_user_projects_time_cost_per_period(first_day: str, user: TUser) -> list:
    session = _get_session()
    statement = select(Project.project_name, Comment.time) \
        .join_from(Comment, Task).join_from(Task, Project) \
        .where(Comment.user_id == user.user_id, Comment.date >= first_day)
    test = session.execute(statement)
    session.close()
    return [list(i) for i in test]


def get_comment_task_path(cost_id: int) -> str:
    session = _get_session()
    task_path = session.query(Task.task_path).join(Comment).filter(Comment.task_id == Task.task_id,
                                                                   Comment.comment_id == cost_id).one()[0]
    session.close()
    return task_path


def remove_comment_db(cost_id: int) -> None:
    session = _get_session()
    comment = session.query(Comment).filter(Comment.comment_id == cost_id).one()
    session.delete(comment)
    session.commit()
    session.close()


def get_bookmarks_user(user: TUser) -> list[UserBookmark]:
    session = _get_session()
    query_bookmarks = session.query(UserBookmark.ub_id, Bookmark.bookmark_name) \
        .join(Bookmark).filter(UserBookmark.user_id == user.user_id).all()
    session.close()
    return query_bookmarks


def remove_users_bookmark_db(id_ub: int) -> None:
    session = _get_session()
    i = session.query(UserBookmark).filter(UserBookmark.ub_id == id_ub).one()
    session.delete(i)
    session.commit()
    session.close()


def get_projects_db() -> list[int]:
    session = _get_session()
    projects_id = session.query(Project.project_id).all()
    session.close()
    return [i[0] for i in projects_id]


async def add_project_in_db(project: KeyboardData) -> None:
    session = _get_session()
    new_project = Project(project_id=project.id,
                          project_name=project.text,
                          project_path=f'/project/{str(project.id)}/')
    session.add(new_project)
    session.commit()
    session.close()


def get_project_tasks_id_db(project_id: str) -> list[int]:
    session = _get_session()
    tasks_id = session.query(Task.task_ws_id).filter(Task.project_id == project_id).all()
    session.close()
    return [i[0] for i in tasks_id]


def get_all_tasks_id_db() -> list[int]:
    session = _get_session()
    tasks_id = session.query(Task.task_ws_id).all()
    session.close()
    return [i[0] for i in tasks_id]


def get_all_projects_id_db() -> list[int]:
    session = _get_session()
    projects_id = session.query(Project.project_id).all()
    session.close()
    return [i[0] for i in projects_id]


def add_task_in_db(task_info: dict, parent_id: str = None) -> None:
    par_id = int(task_info.get('project').get('id')) if parent_id is None else parent_id
    t = Task(task_path=task_info.get('page'),
             project_id=task_info.get('project').get('id'),
             task_name=task_info.get('name'),
             task_ws_id=task_info.get('id'),
             parent_id=par_id
             )
    session = _get_session()
    session.add(t)
    session.commit()
    session.close()


def remove_task_from_db(task_id) -> None:
    session = _get_session()
    i: Task = session.query(Task).filter(Task.task_ws_id == task_id).one()
    i.status = 'removed'
    session.add(i)
    session.commit()
    session.close()


def get_tasks_from_db(parent_id: str) -> list[KeyboardData]:
    session = _get_session()
    child_tasks: list[tuple] = session.query(Task.task_name, Task.task_ws_id) \
        .filter(Task.parent_id == parent_id, Task.status == 'active').all()
    session.close()
    return [KeyboardData(i[0], i[1]) for i in child_tasks]


def get_task_name(task_id: str) -> str:
    session = _get_session()
    name = session.query(Task.task_name).filter(Task.task_ws_id == task_id).one()[0]
    session.close()
    return name


def get_full_task_name(task_id: str) -> str:
    session = _get_session()
    name = session.query(Project.project_name, Task.task_name).join(Project).filter(Task.task_ws_id == task_id).one()
    session.close()
    return ' | '.join(name)


def get_project_id_by_task_id(parent_id) -> str:
    session = _get_session()
    projects_id = [i[0] for i in session.query(Project.project_id).all()]
    if parent_id in projects_id:
        project_id = parent_id
    else:
        project_id = session.query(Task.project_id).filter(Task.task_ws_id == parent_id).one()[0]
    session.close()
    return project_id


def get_list_user_bookmark(user_id: int) -> list[KeyboardData]:
    session = _get_session()
    user_bookmarks: list[tuple] = session.query(Bookmark.bookmark_name, Task.task_ws_id) \
        .join(Bookmark).join(UserBookmark).join(Project) \
        .filter(UserBookmark.user_id == user_id).order_by(Project.project_name, Task.task_name).all()
    session.close()
    return [KeyboardData(i[0], i[1]) for i in user_bookmarks]


def get_all_booked_task_id() -> list[int]:
    session = _get_session()
    q: list[tuple[str]] = session.query(Task.task_ws_id).join(Bookmark).filter(Bookmark.task_id == Task.task_id).all()
    session.close()
    return [int(i[0]) for i in q]


def add_bookmark_into_db(task_ws_id: str) -> None:
    session = _get_session()
    b = Bookmark(task_id=get_task_db_id(task_ws_id),
                 bookmark_name=get_full_task_name(str(task_ws_id)))
    session.add(b)
    session.commit()
    session.close()


def get_bookmark_id(task_id: str) -> int:
    session = _get_session()
    bookmark_id = session.query(Bookmark.bookmark_id).join(Task).filter(Task.task_ws_id == task_id).one()
    session.close()
    return bookmark_id[0]


def get_task_db_id(task_ws_id: str) -> int:
    session = _get_session()
    task_db_id = session.query(Task.task_id).filter(Task.task_ws_id == task_ws_id).one()
    session.close()
    return int(task_db_id[0])


def get_task_ws_id_db(task_id: int) -> str:
    session = _get_session()
    task_ws_db_id = session.query(Task.task_ws_id).filter(Task.task_id == task_id).one()
    session.close()
    return task_ws_db_id[0]


def add_bookmark_to_user(user_id: int, bookmark_id: int) -> None:
    session = _get_session()
    user_book = UserBookmark(user_id=user_id,
                             bookmark_id=bookmark_id)
    session.add(user_book)
    session.commit()
    session.close()


def get_tasks_path(task_id: str) -> str:
    session = _get_session()
    task_path: tuple[str] = session.query(Task.task_path).filter(Task.task_ws_id == task_id).one()
    session.close()
    return task_path[0]


def reformat_date(date: str) -> str:
    format_date: str = date
    if 'today' in date:
        format_date = str(datetime.today())
    return format_date


def add_comment_in_db(comment_id: str, user_id: int, task_ws_id: str, time: str,
                      text: str, date: str) -> None:
    session = _get_session()
    comment = Comment(
        comment_id=int(comment_id),
        user_id=user_id,
        task_id=get_task_db_id(task_ws_id),
        time=time,
        comment_text=text,
        date=reformat_date(date),
        via_bot=True,
    )
    session.add(comment)
    session.commit()
    session.close()


def change_selected_task(user_id: int, task_ws_id: str) -> None:
    session = _get_session()
    i: User = session.query(User).filter(User.user_id == user_id).one()
    i.selected_task = task_ws_id
    session.add(i)
    session.commit()
    session.close()


async def check_comment(com):
    session = _get_session()
    query_project = [i[0] for i in session.query(Project.project_id).all()]
    if com.get('task').get('project').get('id') not in query_project:
        # print("project don't find")  # TODO отдельный лог
        project = Project(
            project_id=com.get('task').get('project').get('id'),
            project_name=com.get('task').get('project').get('name'),
            project_path=com.get('task').get('project').get('page')
        )
        session.add(project)
        # print(com.get('task').get('project').get('id'))
    query_task = [i[0] for i in session.query(Task.task_ws_id).all()]
    if com.get('task').get('id') not in query_task:
        # print("task don't find")
        task = Task(
            task_path=com.get('task').get('page'),
            project_id=com.get('task').get('project').get('id'),
            task_name=com.get('task').get('name'),
            task_ws_id=com.get('task').get('id'),
        )
        session.add(task)
    search_user: User = session.query(User).filter(User.email == com.get('user_from').get('email')).first()
    # print(search_user)
    if search_user:
        task_ws_id = session.query(Task.task_id).filter(Task.task_ws_id == com.get('task').get('id')).one()[0]
        query_com = [i[0] for i in session.query(Comment.comment_id).all()]
        if int(com.get('id')) not in query_com:
            # print("comment don't find")
            comment = Comment(
                comment_id=com.get('id'),
                user_id=search_user.user_id,
                task_id=task_ws_id,
                time=com.get('time'),
                comment_text=com.get('comment'),
                date=com.get('date'),
                via_bot=False,
            )
            session.add(comment)
    session.commit()
    session.close()


async def get_time_notification() -> set[datetime.time]:
    session = _get_session()
    q: set[datetime.time] = session.query(User.notification_time).all()
    session.close()
    return set([(i[0].strftime("%H:%M")) for i in q])


example = {'comment': 'обсуждение вопросов по сайту',
           'date': '2021-11-16',
           'id': '6424851',
           'is_timer': False,
           'money': '0.00',
           'task': {'date_added': '2019-02-19 20:20',
                    'id': '7754791',
                    'name': 'Мелкие трудоемкости',
                    'page': '/project/243605/7754791/',
                    'priority': '1',
                    'project': {'id': '243605',
                                'name': 'Общие задачи (не относящиеся ни к одному '
                                        'проекту)',
                                'page': '/project/243605/'},
                    'status': 'active',
                    'user_from': {'email': 'e.grigoryeva@smde.ru',
                                  'id': '361647',
                                  'name': 'Екатерина Григорьева'},
                    'user_to': {'email': 'e.grigoryeva@smde.ru',
                                'id': '361647',
                                'name': 'Екатерина Григорьева'}},
           'time': '0:18',
           'user_from': {'email': 'e.grigoryeva@smde.ru',
                         'id': '361647',
                         'name': 'Екатерина Григорьева'}}

if __name__ == '__main__':
    pass
