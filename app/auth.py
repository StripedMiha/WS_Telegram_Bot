import datetime
# from pprint import pprint

import sqlalchemy
from sqlalchemy.orm import Session
from typing import Union

from app.db.structure_of_db import User


class TUser:

    def __init__(self, user_id: int, first_name: str = '', last_name: Union[str, None] = ''):
        q: Union[User, None] = self.__get_user_from_db(user_id)
        if q is None:
            self.user_id = user_id
            self.first_name = first_name
            self.last_name = last_name
            self.full_name = self.first_name + ' ' + self.last_name
            self.__email = None
            self.__date_of_input = 'today'
            self.__status = 'wait'
            self.selected_task = None

        else:
            self.user_id = q.user_id
            self.first_name = q.first_name
            self.last_name = q.last_name
            self.full_name = self.first_name + ' ' + self.last_name
            self.__email = q.email
            self.__date_of_input = q.date_of_input
            self.__status = q.status
            self.selected_task = q.selected_task
        self.admin = self.__is_admin()
        self.has_access = self.__has_access()
        self.blocked = self.__is_blocked

    def __is_admin(self):
        return True if self.__status == 'admin' else False

    def __has_access(self):
        return True if self.__status == 'user' or self.__status == 'admin' else False

    def __is_blocked(self):
        return True if self.__status == 'black' else False

    @staticmethod
    def __get_user_from_db(user_id):
        session = _get_session()
        q: Union[None, User] = session.query(User).filter(User.user_id == user_id).one()
        session.close()
        return q

    @classmethod
    def get_users_list(cls):
        session = _get_session()
        q: list[User] = session.query(User).all()  # .user_id, User.first_name, User.last_name, User.__status
        session.close()
        return q

    @classmethod
    def get_admin_id(cls):
        session = _get_session()
        q: int = session.query(User.user_id).filter(User.status == 'admin').first()[0]
        session.close()
        return q

    def change_status(self, new_status: str):
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.status = new_status
        session.add(update_row)
        session.commit()
        session.close()
        self.__status = new_status

    def change_mail(self, new_mail: str):
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.email = new_mail
        session.add(update_row)
        session.commit()
        session.close()
        self.__email = new_mail

    def change_date(self, new_date: str):
        if new_date == 'yesterday':
            timedelta = datetime.timedelta(days=1)
            split_date = ((str(datetime.date.today() - timedelta)).split('-'))
            split_date.reverse()
            new_date = '.'.join(split_date)
        for i in [' ', ',', ':']:
            temp = new_date.split(i)
            new_date = '.'.join(temp)
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.date_of_input = new_date
        session.add(update_row)
        session.commit()
        session.close()
        self.__date_of_input = new_date

    def get_email(self):
        return self.__email

    def get_date(self):
        return self.__date_of_input

    def get_status(self):
        return self.__status


def _get_session():
    engine = sqlalchemy.create_engine("postgresql+psycopg2://postgres:Mig120300SQL@localhost/tele_ws",
                                      echo=False, pool_size=6, max_overflow=10, encoding='latin1')
    session = Session(bind=engine)
    return session
