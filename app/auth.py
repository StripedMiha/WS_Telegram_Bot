import json
import os
from pprint import pprint


dir_name = (os.path.dirname(__file__))
lists_json = {
    'user': "list_users.json",
    'black': "list_black.json",
    'wait': "list_waiting.json"
}


def read_json(file: str):
    with open(os.path.join(dir_name, lists_json[file]), "r", encoding='utf-8') as file_data:
        return json.load(file_data)


def write_json(file: str, content):
    with open(os.path.join(dir_name, lists_json[file]), "w", encoding='utf-8') as file_data:
        json.dump(content, file_data, ensure_ascii=False)


def new_user(input_data: list):
    id_user, f_name, l_name, type_chat = input_data[0], input_data[1], input_data[2], input_data[3]
    user_dict = read_json('wait')
    user = {'id_user': id_user,
            'first_name': f_name,
            'last_name': l_name,
            'status': 'wait'}
    if type_chat == 'private':
        user['private_chat_id'] = id_user
    user_dict[id_user] = user
    write_json('wait', user_dict)


def black_user(input_data: list):
    id_user, f_name, l_name, type_chat = input_data[0], input_data[1], input_data[2], input_data[3]
    user_dict = read_json('black')
    user = {'id_user': id_user,
            'first_name': f_name,
            'last_name': l_name,
            'status': 'black'}
    if type_chat == 'private':
        user['private_chat_id'] = id_user
    user_dict[id_user] = user
    write_json('black', user_dict)


def check_user(input_data, list_of='user'):
    user_dict = read_json(list_of)
    return True if str(input_data) in user_dict.keys() else False


# проверка админ ли пользователь
def check_admin(input_data):
    user_dict = read_json('user')
    if user_dict.get(str(input_data)) is None:
        return False
    return True if (user_dict.get(str(input_data))).get('status') == 'admin' else False


def check_mail(input_data, type_of_data='email'):
    user_dict = read_json('user')
    user_data = user_dict.get(str(input_data))
    user_data = user_data.get(type_of_data)
    if user_data is None:
        return None
    else:
        return user_data


def edit_data(user_id, new_data, type_data):
    user_dict = read_json('user')
    user_dict[str(user_id)][type_data] = new_data
    write_json('user', user_dict)


def add_bookmark(user_id, data: dict):
    user_dict = read_json('user')
    if user_dict[str(user_id)].get('bookmarks') is None:
        user_dict[str(user_id)]['bookmarks'] = [data]
    elif data in user_dict[str(user_id)]['bookmarks']:
        return False
    else:
        user_dict[str(user_id)]['bookmarks'].append(data)
    write_json('user', user_dict)
    return True


def remove_bookmark(user_id, page):
    user_dict = read_json('user')
    user_book: list
    user_book = user_dict.get(str(user_id)).get('bookmarks')
    book_to_del: dict
    for i in user_book:
        if str(page) == i.get('path'):
            book_to_del = i
            break
    user_book.remove(book_to_del)
    user_dict[str(user_id)]['bookmarks'] = user_book
    write_json('user', user_dict)


def get_list_bookmarks(user_id):
    user_dict = read_json('user')
    if user_dict.get(str(user_id)).get('bookmarks') is None:
        return None
    else:
        return user_dict.get(str(user_id)).get('bookmarks')


# получение короткого словаря пользователей
def get_list(select_list):
    user_dict = read_json(select_list)
    get_dict = {}
    for i, j in user_dict.items():
        get_dict[i] = (j['first_name'] + ' ' + j['last_name'])
    return get_dict


# Перемещение пользователя из списка в список
def change_list(user_id, list_from, list_to):
    user_dict = read_json(list_from)
    if user_dict[str(user_id)]['status'] == 'admin':
        print('писюн')
        return None
    user = user_dict.get(user_id)
    del user_dict[user_id]
    write_json(list_from, user_dict)
    user['status'] = list_to
    another_dict = read_json(list_to)
    another_dict[user_id] = user
    write_json(list_to, another_dict)


def add_admin():
    user = {'id_user': '300617281',
            'first_name': 'Mikhail',
            'last_name': 'Ignatenko',
            'private_chat_id': '300617281',
            'status': 'admin'}
    user_dict = {"300617281": user}
    write_json('user', user_dict)
    return None


# print(check_mail(300617281))
# edit_mail(300617281, 'm.ignatenko@smde.ru')
# print(check_mail(300617281))