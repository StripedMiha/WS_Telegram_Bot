from api_keys import SMDE_URL, api_token_worksection
from pprint import pprint

import hashlib
import requests


ENCOD = 'utf-8'
API_KEY = api_token_worksection


def get_all_project_for_user(email):
    action = 'get_projects'
    hash_key = hashlib.md5(action.encode(ENCOD)+API_KEY.encode(ENCOD))

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
    }

    req = requests.get('{SMDE_URL}action={action}&hash={hash}&extra=users'.format(**attributes_requests))
    projects = req.json().get('data')
    user_project = {}
    for i in projects:
        list_email = [j.get('email') for j in i.get('users')]
        if email in list_email:
            project_id = i.get('id')
            name = i.get('name')
            user_project[('id_'+str(project_id))] = name
    return user_project


def get_sub_tasks():
    pass


data = get_all_project_for_user('m.ignatenko@smde.ru')
# pprint(data)
# print(type(data))
# print(len(data))
action = 'get_project'  # Действие на сайте
page = '/project/' + '248239' + '/'

hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD)) #хеширование ключа для доступа к API

requests_text=('{}action={}&page={}&hash={}&extra=users'.format(SMDE_URL, action, page, hash_key.hexdigest()))
response = requests.get(requests_text).json() # Отправляем get запрос
# print()
# pprint(response.get('data').get('users'))
users = response.get('data').get('users')
list = []
for i in users:
    list.append(i.get('email'))

# pprint(list)
