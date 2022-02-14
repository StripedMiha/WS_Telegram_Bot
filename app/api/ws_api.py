from app.KeyboardDataClass import KeyboardData
from app.config_reader import load_config
from pprint import pprint

import logging
import hashlib
import requests
import datetime

from app.create_log import setup_logger

config = load_config("/run/secrets/ws")
# config = load_config("app/keys/ws.ini")

ENCOD = config["ws_token"]["ENCOD"]
API_KEY = config["ws_token"]["api_token_worksection"]
SMDE_URL = config["ws_token"]["SMDE_URL"]

wsapi_logger: logging.Logger = setup_logger("App.back.wsapi", "app/log/wsapi.log")


async def get_all_project_for_user(email, status_filter='active') -> list[KeyboardData]:
    action = 'get_projects'
    hash_key = hashlib.md5(action.encode(ENCOD)+API_KEY.encode(ENCOD))

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'filter': status_filter
    }
    if status_filter is None:
        req = requests.get(
            '{SMDE_URL}action={action}&hash={hash}&extra=users'.format(**attributes_requests))
    else:
        req = requests.get(
            '{SMDE_URL}action={action}&filter={filter}&hash={hash}&extra=users'.format(**attributes_requests))
    projects = req.json().get('data')
    user_project = []
    for i in projects:
        list_email = [j.get('email') for j in i.get('users')]
        if email in list_email:
            project: KeyboardData = KeyboardData(i.get('name'), i.get('id'))
            user_project.append(project)
    return user_project


def search_tasks(page, status_filter='active'):
    action = 'get_tasks'
    hash_key = hashlib.md5(page.encode(ENCOD)+action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'page': page,
        'filter': status_filter
    }
    query = '{SMDE_URL}action={action}&page={page}&show_subtasks=2&hash={hash}&filter={filter}'\
        .format(**attributes_requests)
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
                    for k in j['child']:
                        out[i['id']]['child'][k['id']] = {'name': k['name']}
    return out


async def get_day_costs_from_ws(date: str, one_day: bool):
    wsapi_logger.info('get day costs from ws')
    action = 'get_costs'
    hash_key = hashlib.md5(action.encode(ENCOD) + API_KEY.encode(ENCOD))
    date_start = datetime.date.today().strftime("%d.%m.%Y") if date == 'today' else date
    date_end = date if one_day else datetime.date.today().strftime("%d.%m.%Y")
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'date_b': date_start,
        'date_e': date_end
    }
    query = '{SMDE_URL}action={action}&show_subtasks=2&hash={hash}&datestart={date_b}&dateend={date_e}'.format(
        **attributes_requests)
    req = requests.get(query).json().get('data')
    return req


def get_the_cost_for_check(date: str, page: str):
    wsapi_logger.info('checking add cost')
    action = 'get_costs'
    hash_key = hashlib.md5(page.encode(ENCOD) + action.encode(ENCOD) + API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'page': page,
        'hash': hash_key.hexdigest(),
        'filter': f"(dateadd='{date}')"
    }
    query = '{SMDE_URL}action={action}&page={page}&hash={hash}&filter={filter}'.format(
        **attributes_requests)
    print(query)
    req = requests.get(query).json()
    return req


def remove_cost_ws(page: str, cost_id: int) -> dict:
    action = 'delete_costs'
    hash_key = hashlib.md5(page.encode(ENCOD) + action.encode(ENCOD) + API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'id': cost_id,
        'page': page
    }
    query = '{SMDE_URL}action={action}&page={page}&id={id}&hash={hash}'.format(**attributes_requests)
    req: dict = requests.get(query).json()
    return req


def add_cost(page, user_email, comment, time, date='today'):
    action = 'add_costs'
    hash_key = hashlib.md5(page.encode(ENCOD) + action.encode(ENCOD) + API_KEY.encode(ENCOD))
    if date == 'today':
        date_add = datetime.date.today().strftime("%d.%m.%Y")
    else:
        date_add = date

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'email': user_email,
        'page': page,
        'comment': comment,
        'time': time,
        'date': date_add
    }
    query = '{SMDE_URL}action={action}&page={page}&email_user_from={email}&time={time}' \
            '&date={date}&comment={comment}&hash={hash}'.format(**attributes_requests)
    req = requests.get(query).json()
    # print(req)
    return req


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
    # print('test')
    # pprint(req)
    return req


if __name__ == '__main__':
    t = search_tasks('/project/256242/')
    pprint(t)
