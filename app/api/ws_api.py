from api_keys import SMDE_URL, api_token_worksection
from pprint import pprint

import hashlib
import requests
import datetime
import json
import os


dir_name = (os.path.dirname(__file__))
ENCOD = 'utf-8'
API_KEY = api_token_worksection


def read_json():
    with open(os.path.join(dir_name, '../../tasks_name.json'), "r", encoding='utf-8') as file_data:
        return json.load(file_data)


def write_json(content):
    with open(os.path.join(dir_name, '../../tasks_name.json'), "w", encoding='utf-8') as file_data:
        json.dump(content, file_data, ensure_ascii=False)


def reformat_date(date):
    date = str(date)
    split_date = date.split('-')
    split_date.reverse()
    format_date = '.'.join(split_date)
    return format_date


def check_task_name(path):
    data = read_json()
    if path not in data.keys():
        task_info = get_task_info(path)
        task_name = task_info['data']['project']['name'] + ' // ' + task_info['data']['name'] + '\n'
        data[path] = task_name
        write_json(data)
    return data[path]


async def get_all_project_for_user(email, filter='active'):
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
    user_project = []
    for i in projects:
        list_email = [j.get('email') for j in i.get('users')]
        if email in list_email:
            project_id = i.get('id')
            name = i.get('name')
            user_project.append([name, str(project_id)])
    return user_project


# get_all_project_for_user('m.ignatenko@smde.ru')


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
        query = '{SMDE_URL}action={action}&page={page}&show_subtasks=2&hash={hash}&filter={filter}'.format(**attributes_requests)
    req = requests.get(query)
    tasks = req.json().get('data')
    # pprint(tasks)
    project_task = {}
    for i in tasks:
        task_id = i.get('id')
        task_name = i.get('name')
        project_task[(str(task_id))] = task_name
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

    # for i in tasks:
    #     out[i['id']] = None
    #     if i.get('child') is not None:
    #         for j in i['child']:
    #             out[j['id']] = i['id']
    #             if j.get('child') is not None:
    #                 for k in j['child']:
    #                     out[k['id']] = j['id']






async def get_day_costs_from_ws(date):
    action = 'get_costs'
    hash_key = hashlib.md5(action.encode(ENCOD) + API_KEY.encode(ENCOD))
    if date == 'today' or date == 'сегодня':
        date_check = reformat_date(datetime.date.today())
    elif date == 'yesterday':
        timedelta = datetime.timedelta(days=1)
        date_check = reformat_date(datetime.date.today() - timedelta)
    else:
        date_check = date
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
        'date': date_check
        # 'filter': filter
    }
    query = '{SMDE_URL}action={action}&show_subtasks=2&hash={hash}&datestart={date}&dateend={date}'.format(
        **attributes_requests)
    req = requests.get(query).json().get('data')
    user_list_costs = []
    return req


def get_format_today_costs(user_email, with_id=False, date='today'):
    data = get_day_costs_from_ws(user_email, date)
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
               f"Потрачено: {this_comment['time_cost']}на {this_comment['comment']}\n\n"
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
    if date == 'today':
        date = 'сегодня'
    else:
        date = date
    answer += f"Общее время за {date}: {total_time_str}"
    if total_time[0] + total_time[1] == 0:
        return None
    return answer


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
        date_add = reformat_date(datetime.date.today())
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
