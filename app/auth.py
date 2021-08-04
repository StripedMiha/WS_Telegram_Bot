import json
import os


dir_name = (os.path.dirname(__file__))
lists_json = {
    'users': "list_users.json",
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
    user_dict = read_json('users')
    user = {'id_user': id_user,
            'first_name': f_name,
            'last_name': l_name,
            'status': 'user'}
    if type_chat == 'private':
        user['private_chat_id'] = id_user
    user_dict[id_user] = user
    write_json('users', user_dict)
    list_wait = read_json('wait')
    del list_wait[str(id_user)]
    write_json('wait', list_wait)


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


def check_user(input_data, list_of='users'):
    user_dict = read_json(list_of)
    return True if str(input_data) in user_dict.keys() else False


# проверка админ ли пользователь
def check_admin(input_data):
    user_dict = read_json('users')
    if user_dict.get(str(input_data)) is None:
        return False
    return True if (user_dict.get(str(input_data))).get('status') == 'admin' else False


def check_mail(input_data):
    user_dict = read_json('users')
    user_data = user_dict.get(str(input_data))
    user_email = user_data.get('email')
    if user_email is None:
        return '-'
    else:
        return user_email


def edit_mail(user_id, new_mail):
    user_dict = read_json('users')
    user_dict[str(user_id)]['email'] = new_mail
    write_json('users', user_dict)
    pass


# получение короткого словаря пользователей
def get_list(select_list):
    user_dict = read_json(select_list)
    get_dict = {}
    for i, j in user_dict.items():
        get_dict[i] = (j['first_name'] + ' ' + j['last_name'])
    return get_dict


# бан\разбан пользователя
def change_list(input_data, list_of):
    user_dict = read_json(list_of)
    if user_dict[str(input_data)]['status'] == 'admin':
        print('писюн')
        return None
    user = user_dict.get(input_data)
    del user_dict[input_data]
    write_json(list_of, user_dict)
    if list_of == 'users':
        user['status'] = 'black'
        another_list = 'black'
    else:
        user['status'] = 'user'
        another_list = 'users'
    another_dict = read_json(another_list)
    another_dict[input_data] = user
    write_json(another_list, another_dict)


def add_admin():
    user = {'id_user': '300617281',
            'first_name': 'Mikhail',
            'last_name': 'Ignatenko',
            'private_chat_id': '300617281',
            'status': 'admin'}
    user_dict = {"300617281": user}
    write_json('users', user_dict)
    return None


print(check_mail(300617281))
edit_mail(300617281, 'm.ignatenko@smde.ru')
print(check_mail(300617281))