import datetime
import logging
from datetime import timedelta, date

from sqlalchemy import select, func, and_

from app.KeyboardDataClass import KeyboardData
from app.create_log import setup_logger
from app.db.structure_of_db import get_session, Comment, Project, Task, User

db_logger: logging.Logger = setup_logger("App.back.db", "app/log/db.log")


def date_to_db_format(date: str) -> str:
    try:
        f_date = date.split(".")
        f_date.reverse()
        return '-'.join(f_date)
    except:
        return date


def dec_get_session(func):
    session = get_session()

    def decorated(*arg):
        query = func(session, arg)
        return query

    session.close()
    return decorated


def get_user_days_costs(user_id: int, user_date: str) -> list[tuple[str, timedelta, str, str, int]]:
    """

    :param user_id:
    :param user_date:
    :return: comment_text, time, task_name, project_label, project_name, comment_id
    """
    session = get_session()
    query_comments = session.query(Comment.comment_text, Comment.time, Task.task_name, Project.project_label,
                                   Project.project_name, Comment.comment_id) \
        .join(Comment).join(Project) \
        .filter(Comment.user_id == user_id,
                Comment.date == date_to_db_format(user_date)).order_by(Project.project_label, Task.task_name).all()
    session.close()
    return query_comments


async def get_all_user_day_costs(date: str) -> list[tuple]:
    session = get_session()
    all_comments = session.query(Comment.comment_text, Comment.time, Comment.comment_id) \
        .filter(Comment.date == date_to_db_format(date)).all()
    session.close()
    return all_comments


def get_all_costs_for_period(first_day: str) -> list[list[int, str]]:
    session = get_session()
    q: list[tuple[int, str]] = session.query(Comment.user_id, Comment.time) \
        .filter(Comment.date >= date_to_db_format(first_day), Comment.via_bot == True).all()
    session.close()
    return [list(i) for i in q]


def get_the_user_costs_for_period(user: User, day_from: str) -> list[timedelta]:
    session = get_session()
    q = session.query(Comment.time).filter(Comment.user_id == user.user_id, Comment.date == day_from).all()
    session.close()
    return [i[0] for i in q]


def get_period_user(first_day: str) -> list[int]:
    session = get_session()
    users: list[tuple[int, str]] = session.query(Comment.user_id) \
        .filter(Comment.date >= first_day, Comment.via_bot == True).all()
    session.close()
    return [i[0] for i in users]


def get_the_user_projects_time_cost_per_period(first_day: str, user: User) -> list[list[str, str, timedelta]]:
    session = get_session()
    statement = select(Project.project_label, Project.project_name, Comment.time) \
        .join_from(Comment, Task).join_from(Task, Project) \
        .where(Comment.user_id == user.user_id, Comment.date >= first_day)
    test = session.execute(statement)
    session.close()
    return [list(i) for i in test]


def get_user_costs_per_week(first_day: str, user: User) -> list[Comment]:
    session = get_session()
    comments = session.query(Comment.date, Comment.time, Comment.via_bot).filter(Comment.user_id == user.user_id,
                                                                                 Comment.date >= first_day).all()
    session.close()
    return comments


def get_users_atata_costs(end_day: str = datetime.datetime.today(),
                          first_day: str = datetime.datetime.today() - datetime.timedelta(days=8)
                          ) -> list[tuple[str, str, datetime.date, datetime.timedelta]]:
    session = get_session()
    comments = session.query(User.last_name, User.first_name, Comment.date, func.sum(Comment.time))\
                      .join(Comment.user)\
                      .filter(and_(end_day >= Comment.date, Comment.date >= first_day))\
                      .group_by(User.last_name, User.first_name, Comment.date).all()
    return comments


# example = {'comment': '???????????????????? ???????????????? ???? ??????????',
#            'date': '2021-11-16',
#            'id': '6424851',
#            'is_timer': False,
#            'money': '0.00',
#            'task': {'date_added': '2019-02-19 20:20',
#                     'id': '7754791',
#                     'name': '???????????? ????????????????????????',
#                     'page': '/project/243605/7754791/',
#                     'priority': '1',
#                     'project': {'id': '243605',
#                                 'name': '?????????? ???????????? (???? ?????????????????????? ???? ?? ???????????? '
#                                         '??????????????)',
#                                 'page': '/project/243605/'},
#                     'status': 'active',
#                     'user_from': {'email': 'e.grigoryeva@smde.ru',
#                                   'id': '361647',
#                                   'name': '?????????????????? ????????????????????'},
#                     'user_to': {'email': 'e.grigoryeva@smde.ru',
#                                 'id': '361647',
#                                 'name': '?????????????????? ????????????????????'}},
#            'time': '0:18',
#            'user_from': {'email': 'e.grigoryeva@smde.ru',
#                          'id': '361647',
#                          'name': '?????????????????? ????????????????????'}}

if __name__ == '__main__':
    pass
