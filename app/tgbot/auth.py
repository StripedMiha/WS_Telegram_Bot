import datetime
# from pprint import pprint

from sqlalchemy.exc import NoResultFound
from typing import Union

from app.db.structure_of_db import User, _get_session
from app.exceptions import FutureDate, NoRemindNotification


class TUser:

    def __init__(self, user_id: int, first_name: str = '', last_name: Union[str, None] = ''):
        q: Union[User, None] = self.__get_user_from_db(user_id)
        if isinstance(q, type(None)):
            self.user_id = user_id
            self.first_name = first_name
            self.last_name = '' if isinstance(last_name, type(None)) else last_name
            self.full_name = self.first_name + ' ' + self.last_name
            self.__email = None
            self.__date_of_input = 'today'
            self.__status = 'wait'
            self.selected_task = None
            self.add_new_user()
        else:
            self.user_id = q.user_id
            self.first_name = q.first_name
            self.last_name = q.last_name
            self.full_name = self.first_name + ' ' + self.last_name
            self.__email = q.email
            self.__date_of_input = q.date_of_input
            self.__status = q.status
            self.selected_task = q.selected_task
            self.notification_status: bool = q.notification_status
            self.notification_time: str = q.notification_time.strftime("%H:%M")
            self.remind_notification: datetime.datetime = q.remind_notification \
                if isinstance(q.remind_notification, datetime.datetime) else None
        self.admin = self.__is_admin()
        self.has_access = self.__has_access()
        self.blocked = self.__is_blocked()

    def __is_admin(self):
        return True if self.__status == 'admin' else False

    def __has_access(self):
        return True if self.__status == 'user' or self.__status == 'admin' else False

    def __is_blocked(self):
        return True if self.__status == 'black' else False

    @staticmethod
    def __get_user_from_db(user_id):
        session = _get_session()
        try:
            q: Union[None, User] = session.query(User).filter(User.user_id == user_id).one()
        except NoResultFound:
            return None
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

    def add_new_user(self):
        session = _get_session()
        user = User(
            user_id=self.user_id,
            first_name=self.first_name,
            last_name=self.last_name,
            email=None,
            date_of_input='today',
            status='wait',
            selected_task=None
        )
        session.add(user)
        session.commit()
        session.close()

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
            new_date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")

            print(new_date)
        elif new_date == 'today':
            pass
        else:
            for i in [' ', ',', ':']:
                temp = new_date.split(i)
                new_date = '.'.join(temp)
            temp = new_date.split('.')
            print(temp)
            if datetime.datetime(year=int(temp[2]), month=int(temp[1]), day=int(temp[0])) > datetime.datetime.now():
                raise FutureDate
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.date_of_input = new_date
        session.add(update_row)
        session.commit()
        session.close()
        self.__date_of_input = new_date

    def set_remind_time(self, new_time: Union[datetime.datetime, None]):
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.remind_notification = new_time
        session.add(update_row)
        session.commit()
        session.close()
        self.remind_notification = new_time

    def set_notification_time(self, new_time: datetime.time):
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.notification_time = new_time
        session.add(update_row)
        session.commit()
        session.close()
        self.notification_time = new_time.strftime("%H:%M")

    def toggle_notification_status(self):
        new_status: bool = False if self.notification_status else True
        session = _get_session()
        update_row: User = session.query(User).get(self.user_id)
        update_row.notification_status = new_status
        session.add(update_row)
        session.commit()
        session.close()
        self.notification_status = new_status

    def get_notification_time(self) -> str:
        now: datetime.datetime = datetime.datetime.now()
        return " ".join([now.strftime("%Y-%m-%d"), self.notification_time])

    def get_remind_notification_time(self) -> str:
        if isinstance(self.remind_notification, type(None)):
            raise NoRemindNotification
        return self.remind_notification.strftime("%Y-%m-%d %H:%M")

    def get_email(self) -> str:
        return self.__email

    def get_date(self) -> str:
        return self.__date_of_input

    def get_status(self) -> str:
        return self.__status
