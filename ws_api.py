from api_keys import SMDE_URL, api_token_worksection
from pprint import pprint

import hashlib
import requests
import datetime


ENCOD = 'utf-8'
API_KEY = api_token_worksection


def reformat_date(date):
    date = str(date)
    split_date = date.split('-')
    split_date.reverse()
    format_date = '.'.join(split_date)
    return format_date


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
    req = requests.get(query)
    tasks = req.json().get('data')
    project_task = {}
    for i in tasks:
        task_id = i.get('id')
        task_name = i.get('name')
        project_task[('task_id_'+str(task_id))] = task_name
    return project_task


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


def get_today_costs(email):
    action = 'get_costs'
    hash_key = hashlib.md5(action.encode(ENCOD) + API_KEY.encode(ENCOD))
    date_today = reformat_date(datetime.date.today())

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'date': date_today
        # 'filter': filter
    }
    query = '{SMDE_URL}action={action}&show_subtasks=2&hash={hash}&datestart={date}'.format(
        **attributes_requests)
    req = requests.get(query).json().get('data')
    # pprint(req)
    user_list_costs = []
    for i in req:
        if i.get('user_from').get('email') == email:
            user_list_costs.append(i)
    return user_list_costs


def get_format_today_costs(user_email, with_id=False):
    data = get_today_costs(user_email)
    answer = ''
    all_comment = []
    total_time = [0, 0]
    for i in data:
        # pprint(i)
        time = i.get('time')
        hours = int(time.split(':')[0])
        minutes = int(time.split(':')[1])
        time_str = ''
        if hours > 0:
            if hours == 1:
                word = 'час'
            elif 2 <= hours <= 4:
                word = 'часа'
            else:
                word = 'часов'
            time_str += f'{hours} {word} '
        if minutes > 0:
            time_str += f'{minutes} минут '
        this_comment = {'comment': i.get('comment'),
                        'task_name': i.get('task').get('name'),
                        'project_name': i.get('task').get('project').get('name'),
                        'time_cost': time_str,
                        'page': i.get('task').get('page'),
                        'comment_id': i.get('id')
                        }
        all_comment.append(this_comment)
        text = f"Проект: {this_comment['project_name']}\n" \
               f"Задача: {this_comment['task_name']}\n" \
               f"Потрачено {this_comment['time_cost']}на {this_comment['comment']}\n\n"
        answer += text
        total_time = [total_time[0] + hours, total_time[1] + minutes]
    # pprint(all_comment)
    if with_id:
        return all_comment
    total_time = [total_time[0] + total_time[1] // 60, total_time[1] % 60]
    total_time_str = ''
    if total_time[0] > 0:
        if total_time[0] == 1:
            word = 'час'
        elif 2 <= total_time[0] <= 4:
            word = 'часа'
        else:
            word = 'часов'
        total_time_str += f'{total_time[0]} {word} '
    if total_time[1] > 0:
        total_time_str += f'{total_time[1]} минут '
    answer += f'Общее время за сегодня: {total_time_str}'
    if total_time[0] + total_time[1] == 0:
        return None
    return answer


def remove_cost(page, cost_id):
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
    req = requests.get(query).json()
    return req.get('status')


def add_cost(page, user_email, comment, time):
    action = 'add_costs'
    hash_key = hashlib.md5(page.encode(ENCOD) + action.encode(ENCOD) + API_KEY.encode(ENCOD))

    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'email': user_email,
        'page': page,
        'comment':comment,
        'time':time
    }
    query = '{SMDE_URL}action={action}&page={page}&email_user_from={email}&time={time}' \
            '&comment={comment}&hash={hash}'.format(**attributes_requests)
    req = requests.get(query).json()
    print(req)
    return req.get('status')

# pprint(get_tasks('/project/246875/'))
# get_subtasks('/project/243605/8297507/')
# pprint(search_tasks('/project/243605/8290051/8349103/'), width=160)
# get_subtasks('/project/243605/8297507/7604753/')
