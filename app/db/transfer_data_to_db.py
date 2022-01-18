import json
import hashlib
import re

import requests

from sqlalchemy.orm import Session
from sqlalchemy import MetaData

from app.config_reader import load_config
from structure_of_db import engine, Task, Project, Bookmark, User, UserBookmark
from pprint import pprint


config = load_config("keys/ws.ini")
ENCOD = config["ws_token"]["ENCOD"]
API_KEY = config["ws_token"]["api_token_worksection"]
SMDE_URL = config["ws_token"]["SMDE_URL"]

PROJECT_NAME_TEMPLATE = r'[a-z]{3,5}-\d{3}([a-z]\d\d)?'


metadata = MetaData()
session = Session(bind=engine)


def get_task_info(page):
    action = 'get_task'
    hash_key = hashlib.md5(page.encode(ENCOD) + action.encode(ENCOD) + API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page
    }
    query = '{SMDE_URL}action={action}&page={page}&hash={hash}'.format(**attributes_requests)
    req = requests.get(query).json()
    return req


def get_booked_task():
    for list_data in ['list_users.json', 'list_black.json']:
        with open(list_data, 'r', encoding='utf-8') as file_in:
            text: dict = json.load(file_in)
        for key, value in text.items():
            # print(key)
            # pprint(value)
            user = User(user_id=value['id_user'],
                        first_name=value['first_name'],
                        last_name=value['last_name'],
                        status=value['status'],
                        )
            if value.get('email'):
                user.email = value['email']
            if value.get('date'):
                user.date_of_input = value['date']
            session.add(user)
            b = value.get('bookmarks')
            if b:
                for i in value['bookmarks']:
                    r = (get_task_info(i['path']))
                    # pprint(r)
                    if not session.query(Project).filter(Project.project_id == r['data']['project']['id']).all():
                        project = Project(
                            project_id=r['data']['project']['id'],
                            project_name=r['data']['project']['name'],
                            project_path=r['data']['project']['page'],
                        )
                        session.add(project)
                    if not session.query(Task).filter(Task.task_ws_id == r['data']['id']).all():
                        task = Task(
                            task_path=r['data']['page'],
                            project_id=r['data']['project']['id'],
                            task_name=r['data']['name'],
                            task_ws_id=r['data']['id']
                        )
                        session.add(task)

                    q = session.query(Task.task_name, Project.project_name, Task.task_id).join(Project)\
                        .filter(Task.task_ws_id == r['data']['id']).first()
                    print(1111)
                    pprint(q)
                    project_name = re.search(PROJECT_NAME_TEMPLATE, q[1])
                    # print(project_name[0] if project_name else q[-1])
                    task_name = re.sub(PROJECT_NAME_TEMPLATE, '', q[0])
                    # print(task_name)
                    print(project_name[0] if project_name else q[1], task_name.strip(' '))
                    print('task_id -', q[2])
                    print(1111)
                    book_name = project_name[0] + ' | ' + task_name.strip(' ') \
                        if project_name else (
                            'Общие задачи' if 'Общие задачи' in q[1] else q[1] + ' | ' + task_name.strip(' '))
                    pprint(book_name)
                    print(type(book_name))
                    bookmark = Bookmark(
                        task_id=q[2],
                        bookmark_name=book_name
                    )
                    session.add(bookmark)
                    print(bookmark.task_id)
                    print('--------------------------------------------------')
                    q_book = session.query(Bookmark.bookmark_id, Bookmark.bookmark_name).join(Task)\
                        .filter(Task.task_id == q[2]).first()
                    pprint(q_book)
                    usersbook = UserBookmark(
                        user_id=value['id_user'],
                        bookmark_id=q_book[0]
                    )
                    session.add(usersbook)

            print('==================================================')
        session.commit()

        print(123)


get_booked_task()
# print(111)
# q = session.query(User).all()
# print(222)
# for i in q:
#     print(i.first_name)
#     time.sleep(1)
# session = Session(bind=engine)
# print(1)
# if not session.query(Project).filter(Project.project_id == '243605').all():
#     print('такого нет, создаём')
# else:
#     print('уже есть')
#
# session
# print(2)
