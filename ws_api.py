from api_keys import SMDE_URL, api_token_worksection
from pprint import pprint

import hashlib
import requests


ENCOD = 'utf-8'
API_KEY = api_token_worksection


def get_all_project_for_user(email, filter='active'):
    action = 'get_projects'
    hash_key = hashlib.md5(action.encode(ENCOD)+API_KEY.encode(ENCOD))

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'filter': filter
    }
    if filter is None:
        req = requests.get('{SMDE_URL}action={action}&hash={hash}&extra=users'.format(**attributes_requests))
    else:
        req = requests.get('{SMDE_URL}action={action}&filter={filter}&hash={hash}&extra=users'.format(**attributes_requests))
    projects = req.json().get('data')
    user_project = {}
    for i in projects:
        list_email = [j.get('email') for j in i.get('users')]
        if email in list_email:
            project_id = i.get('id')
            name = i.get('name')
            user_project[('id_'+str(project_id))] = name
    return user_project


def get_tasks(page, filter='active'):
    action = 'get_tasks'
    hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page,
        'filter': filter
    }
    if filter is None:
        query = '{SMDE_URL}action={action}&page={page}&hash={hash}'.format(**attributes_requests)
    else:
        query = '{SMDE_URL}action={action}&page={page}&hash={hash}&filter={filter}'.format(**attributes_requests)
    # query = '{SMDE_URL}action={action}&page={page}&show_subtasks=2&hash={hash}'.format(**attributes_requests)
    print(query)
    req = requests.get(query)
    # pprint(req.json()).get('data')
    # print(len(page.split('/')))
    tasks = req.json().get('data')
    project_task = {}
    # pprint(tasks[0].get('child'))
    for i in tasks:
        task_id = i.get('id')
        task_name = i.get('name')
        project_task[('task_id_'+str(task_id))] = task_name
    return project_task


def get_subtasks(page):
    action = 'get_tasks'
    hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page
    }
    query = '{SMDE_URL}action={action}&page={page}&show_subtasks=2&hash={hash}'.format(**attributes_requests)
    print(query)
    req = requests.get(query)
    tasks = req.json().get('data')
    project_task = {}
    subtask = page.split('/')[-2]
    pprint(tasks)
    # for i in tasks:
    #     pprint(i)
    #     if i['id'] == subtask:
    #         # pprint(i)
    #         for j in i.get('child'):
    #             task_id = j.get('id')
    #             task_name = j.get('name')
    #             project_task[('task_id_'+str(task_id))] = task_name
    # pprint(project_task)
    # return project_task


def search_tasks(page, filter='active'):
    action = 'get_tasks'
    hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page,
        'filter': filter
    }
    query = '{SMDE_URL}action={action}&page={page}&show_subtasks=2&hash={hash}&filter={filter}'.format(**attributes_requests)
    # print(query)
    req = requests.get(query)
    tasks = req.json().get('data')
    out = {}
    for i in tasks:
        out[i['id']] = {'name': i['name']}
        if i.get('child') is not None:
            out[i['id']]['child'] = {}
            for j in i['child']:
                out[i['id']]['child'][j['id']] = {'name': j['name']}
                if j.get('child') is not None:
                    # out[i['id']]['child'][j['id']] = {
                    for k in j['child']:
                        out[i['id']]['child'][k['id']] = {'name': k['name']}
    # pprint(out, width=160)
    return out


# pprint(get_tasks('/project/246875/'))
# get_subtasks('/project/243605/8297507/')
# pprint(search_tasks('/project/243605/8290051/8349103/'), width=160)
# get_subtasks('/project/243605/8297507/7604753/')

