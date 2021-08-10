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


def get_tasks(page):
    action = 'get_tasks'
    hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page
    }

    req = requests.get('{SMDE_URL}action={action}&page={page}&hash={hash}'.format(**attributes_requests))
    tasks = req.json().get('data')
    project_task = {}
    for i in tasks:
        task_id = i.get('id')
        task_name = i.get('name')
        project_task[('id_task_'+str(task_id))] = task_name
    return project_task


    pass


# get_tasks('/project/257358/')