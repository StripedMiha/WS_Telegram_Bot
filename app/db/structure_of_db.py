from datetime import datetime, date, time, timedelta
import time
from pprint import pprint
from typing import Optional

import sqlalchemy
from sqlalchemy.exc import NoResultFound

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, String, Integer, Column, Text, Date, Boolean, DateTime, Table  # , Table, , Numeric
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Session, relationship

from app.KeyboardDataClass import KeyboardData
from app.config_reader import load_config

from app.start_type import start_from_docker

if start_from_docker:
    config = load_config("/run/secrets/db")
else:
    config = load_config("app/keys/db.ini")

psql_user = config["db"]["user"]
password = config["db"]["password"]
bd_name = config["db"]["bd_name"]
host = config["db"]["host"]

bd_url = f"postgresql+psycopg2://{psql_user}:{password}@{host}/{bd_name}"

engine = sqlalchemy.create_engine(bd_url, echo=False, pool_size=6, max_overflow=10, encoding='latin1')
Base = declarative_base()
metadata = MetaData()


def get_session():
    f_session = Session(bind=engine)
    return f_session


session = get_session()


class Project(Base):
    __tablename__ = 'projects'
    Base.metadata = metadata
    project_id = Column(String(15), primary_key=True, nullable=False)
    project_name = Column(Text(), nullable=False)
    project_path = Column(String(40), nullable=False)

    def __repr__(self):
        return f"{self.project_id}, {self.project_name}, {self.project_path}"

    @staticmethod
    def new_project(project_data: KeyboardData):
        project = Project(
            project_id=project_data.id,
            project_name=project_data.text,
            project_path=f'/project/{str(project_data.id)}/'
        )
        session.add(project)
        session.commit()

    @staticmethod
    def get_project(project_id: str):
        return session.query(Project).filter(Project.project_id == project_id).one()

    @classmethod
    def get_all_projects_id_from_db(cls) -> set[int]:
        return {i[0] for i in session.query(Project.project_id).all()}


class Task(Base):
    __tablename__ = 'tasks'
    Base.metadata = metadata
    task_id = Column(Integer(), primary_key=True, nullable=False)
    task_path = Column(String(40), nullable=False)
    project_id = Column(String(15), ForeignKey('projects.project_id'), nullable=False)
    task_name = Column(Text())
    task_ws_id = Column(String(15), nullable=False, unique=True)
    parent_id = Column(Integer())
    status = Column(String(10), default='active')

    project = relationship("Project", backref="tasks", uselist=False)

    def __repr__(self):
        return f"db_id - {self.task_id}, ws_id - {self.task_ws_id}, path - {self.task_path}," \
               f" project_id - {self.project_id}, name - {self.task_name}, status - {self.status}"

    def full_name(self):
        return f"{self.project.project_name} | {self.task_name}"

    @staticmethod
    def new_task(task_info: dict, parent_id: str = None) -> None:
        par_id = int(task_info.get('project').get('id')) if parent_id is None else parent_id
        t = Task(task_path=task_info.get('page'),
                 project_id=task_info.get('project').get('id'),
                 task_name=task_info.get('name'),
                 task_ws_id=task_info.get('id'),
                 parent_id=par_id,
                 status="active"
                 )
        session.add(t)
        session.commit()

    def update(self, parent_id: int):
        self.parent_id = parent_id
        self.status = "active"
        session.commit()

    def mark_remove(self):
        self.status = "removed"
        session.commit()

    @staticmethod
    def get_subtasks(task_ws_is) -> list:
        sub_tasks: list[Task] = session.query(Task).filter(Task.parent_id == task_ws_is, Task.status == "active").all()
        return sub_tasks

    @staticmethod
    def get_task(task_id: int):
        try:
            return session.query(Task).filter(Task.task_id == task_id).one()
        except NoResultFound:
            print("Task is not exists")

    @staticmethod
    def get_task_via_ws_id(task_ws_id: str):
        try:
            return session.query(Task).filter(Task.task_ws_id == task_ws_id).one()
        except NoResultFound:
            print("Task is not exists")


class Bookmark(Base):
    __tablename__ = 'bookmarks'
    Base.metadata = metadata
    bookmark_id = Column(Integer(), primary_key=True, nullable=False)
    task_id = Column(Integer(), ForeignKey('tasks.task_id'), nullable=False)
    bookmark_name = Column(Text(), nullable=False)
    task: Task = relationship("Task", uselist=False)

    def __repr__(self):
        return f"bookmark_id - {self.bookmark_id} | bookmark_name - {self.bookmark_name} | " \
               f"task_id - {self.task_id}"

    @staticmethod
    def get_bookmark(task_id: int):
        try:
            task: Task = Task.get_task_via_ws_id(str(task_id))
            return session.query(Bookmark).filter(Bookmark.task_id == task.task_id).one()
        except NoResultFound:
            task: Task = Task.get_task_via_ws_id(str(task_id))
            bookmark_name = f"{task.task_name} | {task.project.project_name}"
            new_bookmark = Bookmark(task_id=task.task_id,
                                    bookmark_name=bookmark_name)
            session.add(new_bookmark)
            session.commit()
            return Bookmark.get_bookmark(task_id)

    @staticmethod
    def get_bookmark_by_id(bookmark_id: int):
        try:
            return session.query(Bookmark).filter(Bookmark.bookmark_id == bookmark_id).one()
        except NoResultFound:
            print("bookmark is not exist")


user_bookmark = Table('user_bookmark', Base.metadata,
                      Column("user_id", Integer(), ForeignKey('users.user_id'), nullable=False),
                      Column("bookmark_id", Integer(), ForeignKey('bookmarks.bookmark_id'), nullable=False)
                      )


user_status = Table("user_status", Base.metadata,
                    Column("user_id", Integer(), ForeignKey("users.user_id"), nullable=False),
                    Column("status_id", Integer(), ForeignKey("statuses.status_id"), nullable=False)
                    )


class Status(Base):
    __tablename__ = "statuses"
    Base.metadata = metadata
    status_id = Column(Integer(), primary_key=True, nullable=False)
    status_name = Column(String(20), nullable=False)

    def __repr__(self):
        return f'{self.status_name}'

    @staticmethod
    def get_users(status: str) -> list:
        searched_status: Status = Status.get_status(status)
        return [i for i in session.query(User).all() if searched_status in i.statuses]

    @staticmethod
    def get_status(status: str):
        return session.query(Status).filter(Status.status_name == status).one()


class User(Base):
    __tablename__ = 'users'
    Base.metadata = metadata
    user_id = Column(Integer(), primary_key=True, nullable=False)
    email = Column(String(30))
    first_name: str = Column(String(50))
    last_name = Column(String(50))
    date_of_input = Column(String(15))
    selected_task = Column(String(15), ForeignKey('tasks.task_ws_id'), nullable=True, unique=False)
    notification_status = Column(Boolean, default=True)
    notification_time = Column(DateTime, default='')
    remind_notification = Column(DateTime)

    default_task: Task = relationship("Task", uselist=False)

    statuses: list[Status] = relationship("Status", secondary=user_status)
    bookmarks: list[Bookmark] = relationship("Bookmark", secondary=user_bookmark)

    def __repr__(self):
        return f"\n{self.statuses} {self.full_name()}, id{self.user_id}\nЗадача по умолчанию: id" \
               f"{self.default_task.task_ws_id if self.default_task else 'NONE'} - " \
               f"{self.default_task.task_name if self.default_task else ''} " \
               f"на дату {self.date_of_input}\n" \
               f"Статус уведомлений - {self.notification_status} на {self.notification_time} или " \
               f"{self.remind_notification}"

    def blocked(self) -> bool:
        b_status = Status.get_status('black')
        return True if b_status in self.statuses else False

    def is_admin(self) -> bool:
        a_status = Status.get_status('admin')
        return True if a_status in self.statuses and not self.blocked() else False

    def has_access(self) -> bool:
        u_status = Status.get_status('user')
        return True if u_status in self.statuses and not self.blocked() else False

    def get_status(self) -> list[str]:
        return self.statuses

    def get_date(self) -> str:
        return self.date_of_input

    def get_email(self) -> str:
        return self.email

    def full_name(self) -> str:
        return " ".join([self.first_name, self.last_name])

    def get_notification_time(self) -> str:
        now: datetime = datetime.now()
        not_time = self.notification_time
        return " ".join([now.strftime("%Y-%m-%d"), not_time.strftime("%H:%M")])

    @classmethod
    def get_admin_id(cls):
        admin_id: int = session.query(User.user_id).filter(User.statuses == 'admin').first()[0]
        session.close()
        return admin_id

    def change_date(self, new_date: str):
        self.date_of_input = new_date
        session.commit()

    def change_mail(self, new_email: str):
        self.email = new_email
        session.commit()

    def change_status(self, new_status: str, old_status: Optional[str] = None):
        n_status: Status = Status.get_status(new_status)
        self.statuses.append(n_status)
        if old_status:
            o_status: Status = Status.get_status(old_status)
            self.statuses.remove(o_status)
        session.add(self)
        session.commit()

    def change_default_task(self, new_default_task_id: str) -> str:
        self.selected_task = new_default_task_id
        session.commit()
        return '\n'.join(['Выбранная задача:', self.default_task.full_name()])

    def toggle_notification_status(self):
        self.notification_status = not self.notification_status
        session.commit()

    def set_notification_time(self, new_time: datetime.time):
        self.notification_time = new_time
        session.commit()

    def get_remind_notification_time(self) -> str:
        if isinstance(self.remind_notification, type(None)):
            return 'XX:XX'
        return self.remind_notification.strftime("%H:%M")

    def set_remind_time(self, new_time: Optional[datetime]):
        self.remind_notification = new_time
        session.commit()

    def add_bookmark(self, bookmark: Bookmark):
        self.bookmarks.append(bookmark)
        session.add(self)
        session.commit()

    def remove_bookmark(self, bookmark: Bookmark):
        self.bookmarks.remove(bookmark)
        session.commit()

    @staticmethod
    def get_user(user_id: int, *args):

        try:
            return session.query(User).filter(User.user_id == user_id).one()
        except NoResultFound:
            first_name, last_name = args
            user = User(
                user_id=user_id,
                first_name=first_name,
                last_name=last_name,
                email=None,
                date_of_input='today',
                status='wait',
                selected_task=None,
                notification_status=True,
                notification_time=time(hour=18, minute=30),
                remind_notification=None
            )
            session.add(user)
            session.commit()
            return User.get_user(user_id)

    @classmethod
    def get_users_list(cls):
        q: list[User] = session.query(User).all()  # .user_id, User.first_name, User.last_name, User.__status
        return q


# class UserBookmark(Base):
#     __tablename__ = 'user_bookmark'
#     ub_id = Column(Integer(), primary_key=True, nullable=False)
#     user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
#     bookmark_id = Column(Integer(), ForeignKey('bookmarks.bookmark_id'), nullable=False)


class Comment(Base):
    __tablename__ = 'comments'
    Base.metadata = metadata

    comment_id = Column(Integer(), primary_key=True, nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'))
    task_id = Column(Integer(), ForeignKey('tasks.task_id'))
    time = Column(String(10))
    comment_text = Column(Text())
    date = Column(Date)
    via_bot = Column(Boolean)

    task: Task = relationship("Task")

    def __repr__(self):
        return f"comment_id - {self.comment_id}, user_id - {self.user_id}, task_id - {self.task_id}," \
               f" via_bot - {self.via_bot}, date - {self.date}, time - {self.time}, text - {self.comment_text}"

    @staticmethod
    def add_comment_in_db(comment_id: int, user_id: int, task_ws_id: int,
                          comment_time: str, text: str, comment_date: str, via_bot: bool = True):
        comment = Comment(
            comment_id=comment_id,
            user_id=user_id,
            task_id=task_ws_id,
            time=comment_time,
            comment_text=text,
            date=reformat_date(comment_date),
            via_bot=via_bot,
        )
        session.add(comment)
        session.commit()

    def remove(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def get_comment(cost_id: int):

        try:
            return session.query(Comment).filter(Comment.comment_id == cost_id).one()
        except NoResultFound:
            print("Comment not exist")


def reformat_date(str_date: str) -> str:
    format_date: str = str_date
    if 'today' in str_date:
        format_date = str(datetime.today())
    else:
        format_date = date_to_db_format(format_date)
    return format_date


def date_to_db_format(str_date: str) -> str:
    try:
        f_date = str_date.split(".")
        f_date.reverse()
        return '-'.join(f_date)
    except:
        return str_date


# Base.metadata.create_all(engine)
