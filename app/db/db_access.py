import logging
from datetime import datetime

from sqlalchemy import select

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


def get_user_days_costs(user_id: int, user_date: str) -> list[tuple]:
    session = get_session()
    query_comments = session.query(Comment.comment_text, Comment.time, Task.task_name, Project.project_name,
                                   Comment.comment_id) \
        .join(Comment).join(Project) \
        .filter(Comment.user_id == user_id,
                Comment.date == date_to_db_format(user_date)).order_by(Project.project_name, Task.task_name).all()
    session.close()
    return query_comments


async def get_all_user_day_costs(date: str) -> list[tuple]:
    session = get_session()
    all_comments = session.query(Comment.comment_text, Comment.time, Comment.comment_id) \
        .filter(Comment.date == date_to_db_format(date)).all()
    session.close()
    return all_comments


def get_all_costs_for_period(first_day: str):
    session = get_session()
    q = session.query(Comment.user_id, Comment.time) \
        .filter(Comment.date >= date_to_db_format(first_day), Comment.via_bot == True).all()
    session.close()
    return [list(i) for i in q]


def get_the_user_costs_for_period(user: User, day_from: str) -> list:
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


def get_the_user_projects_time_cost_per_period(first_day: str, user: User) -> list:
    session = get_session()
    statement = select(Project.project_name, Comment.time) \
        .join_from(Comment, Task).join_from(Task, Project) \
        .where(Comment.user_id == user.user_id, Comment.date >= first_day)
    test = session.execute(statement)
    session.close()
    return [list(i) for i in test]


def get_user_costs_per_week(first_day: str, user: User) -> list:
    session = get_session()
    comments = session.query(Comment.date, Comment.time, Comment.via_bot).filter(Comment.user_id == user.user_id,
                                                                                 Comment.date >= first_day).all()
    session.close()
    return comments


async def check_project(com: dict, query_project: set):
    if com.get('task').get('project').get('id') not in query_project:
        db_logger.info("project don't find")
        project_data: KeyboardData = KeyboardData(com.get('task').get('project').get('name'),
                                                  com.get('task').get('project').get('id'))
        Project.new_project(project_data)
        db_logger.info('add project with id%s' % com.get('task').get('project').get('id'))
    else:
        db_logger.info('the project with id%s already exists' % com.get('task').get('project').get('id'))


async def check_task(com: dict, query_task: set):
    if com.get('task').get('id') not in query_task:
        db_logger.info("task don't find")
        parent_id: Task = com.get('task').get('page').strip("/").split("/")[-2]
        Task.new_task(com.get('task'), parent_id)
        db_logger.info('add task with id%s' % com.get('task').get('id'))
    else:
        db_logger.info('the task with id%s already exists' % com.get('task').get('id'))


async def check_comment(com: dict, session, query_project: set, query_task: set, query_com: set):
    db_logger.info('start comment check')
    if int(com.get('id')) not in query_com:
        await check_project(com, query_project)
        await check_task(com, query_task)
        db_logger.info('start user check')
        search_user: User = session.query(User).filter(User.email == com.get('user_from').get('email')).first()
        if search_user:
            db_logger.info('user with id%s was found' % search_user.user_id)
            task_db_id = session.query(Task.task_id).filter(Task.task_ws_id == com.get('task').get('id')).one()[0]
            db_logger.info("comment don't find")
            Comment.add_comment_in_db(int(com.get('id')), search_user.user_id, task_db_id, com.get('time'),
                                         com.get('comment'), com.get('date'), False)
            db_logger.info("add comment with id%s" % com.get('id'))


async def check_comments(coms):
    session = get_session()
    db_logger.info('start comments check')
    query_project = {i[0] for i in session.query(Project.project_id).all()}
    query_task = {i[0] for i in session.query(Task.task_ws_id).all()}
    query_com = {i[0] for i in session.query(Comment.comment_id).all()}
    for com in coms:
        await check_comment(com, session, query_project, query_task, query_com)


# example = {'comment': 'обсуждение вопросов по сайту',
#            'date': '2021-11-16',
#            'id': '6424851',
#            'is_timer': False,
#            'money': '0.00',
#            'task': {'date_added': '2019-02-19 20:20',
#                     'id': '7754791',
#                     'name': 'Мелкие трудоемкости',
#                     'page': '/project/243605/7754791/',
#                     'priority': '1',
#                     'project': {'id': '243605',
#                                 'name': 'Общие задачи (не относящиеся ни к одному '
#                                         'проекту)',
#                                 'page': '/project/243605/'},
#                     'status': 'active',
#                     'user_from': {'email': 'e.grigoryeva@smde.ru',
#                                   'id': '361647',
#                                   'name': 'Екатерина Григорьева'},
#                     'user_to': {'email': 'e.grigoryeva@smde.ru',
#                                 'id': '361647',
#                                 'name': 'Екатерина Григорьева'}},
#            'time': '0:18',
#            'user_from': {'email': 'e.grigoryeva@smde.ru',
#                          'id': '361647',
#                          'name': 'Екатерина Григорьева'}}

if __name__ == '__main__':
    pass
