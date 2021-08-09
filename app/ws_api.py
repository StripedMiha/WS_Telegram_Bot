from requests.models import Response
from config.api_keys import SMDE_URL, api_token_worksection

import hashlib
import json
import requests


ENCOD = 'utf-8'
API_KEY = api_token_worksection


def get_all_project():
    action='get_projects'
    hash_key=hashlib.md5(action.encode(ENCOD)+API_KEY.encode(ENCOD))
    attributes_requests = {
        'SMDE_URL': SMDE_URL,
        'action': action,
        'hash': hash_key.hexdigest(),
    }
    response = requests.get('{SMDE_URL}action={action}&hash={hash}'.format(**attributes_requests))
    pass


def get_sub_tasks():
    pass


print(get_all_project())