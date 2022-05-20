import os
from datetime import datetime, date, time, timedelta
from pprint import pprint
from typing import Optional, Union

import sqlalchemy
from sqlalchemy.exc import NoResultFound

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, String, Integer, Column, Text, Date, Boolean, DateTime, Table, Interval, LargeBinary
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
host = config["db"]["host"] if os.environ.get("IS_DOCKER", False) else "localhost"

bd_url = f"postgresql+psycopg2://{psql_user}:{password}@{host}/{bd_name}"
print(bd_url)

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
    project_id: int = Column(Integer(), primary_key=True)
    project_ws_id: str = Column(String(15), nullable=True)
    project_label: str = Column(String(20), nullable=True, unique=True)
    project_name: str = Column(Text(), nullable=False)
    project_path: str = Column(String(40), nullable=True)
    project_status: str = Column(String(15), nullable=False)
    project_description: str = Column(Text(), nullable=True)
    project_image: bytes = Column(LargeBinary(), nullable=True)
    date_create: datetime = Column(DateTime(), default=datetime.now())
    date_update: datetime = Column(DateTime(), nullable=True)

    def __repr__(self):
        if self.project_label:
            return f"{self.project_label} {self.project_name}"
        return self.project_name

    @staticmethod
    def new_project(project_label: str, project_name: str, project_description: str):
        project = Project(
            project_status="active",
            project_label=project_label,
            project_name=project_name,
            project_description=project_description,
            date_create=datetime.now(),
            date_update=None
        )
        session.add(project)
        session.commit()
        print(project)
        returning_project = Project.get_project_by_label(project_label)
        return returning_project

    def archive_project(self):
        Changes.new(self.__tablename__, 'project_status', self.project_status, "archive")
        self.project_status = "archive"
        self.date_update = datetime.now()
        session.commit()

    def activate_project(self):
        Changes.new(self.__tablename__, 'project_status', self.project_status, "active")
        self.project_status = "active"
        self.date_update = datetime.now()
        session.commit()

    def redescription(self, new_description: str):
        Changes.new(self.__tablename__, 'project_description', self.project_description, new_description)
        self.project_description = new_description
        self.date_update = datetime.now()
        session.commit()

    def rename(self, new_name: str):
        Changes.new(self.__tablename__, 'project_name', self.project_name, new_name)
        self.project_name = new_name
        self.date_update = datetime.now()
        session.commit()

    def relabel(self, new_label: str):
        Changes.new(self.__tablename__, 'project_label', self.project_label, new_label)
        self.project_label = new_label
        self.date_update = datetime.now()
        session.commit()

    @staticmethod
    def get_last_project():
        return session.query(Project).all()

    @staticmethod
    def get_project(project_id: int):
        return session.query(Project).filter(Project.project_id == project_id).one()

    @staticmethod
    def get_project_by_ws(project_ws_id: str):
        return session.query(Project).filter(Project.project_id == project_ws_id).one()

    @classmethod
    def get_all_projects_id_from_db(cls) -> set[int]:
        return {i[0] for i in session.query(Project.project_id).all()}

    @staticmethod
    def get_project_by_label(label: str):
        try:
            project = session.query(Project).filter(Project.project_label == label).one()
            return project
        except NoResultFound:
            return None


class Task(Base):
    __tablename__ = 'tasks'
    Base.metadata = metadata
    task_id: int = Column(Integer(), primary_key=True, nullable=False)
    task_ws_id: int = Column(Integer())
    task_path: str = Column(String(40), nullable=True)
    project_id: int = Column(Integer(), ForeignKey("projects.project_id"), nullable=False)
    task_name: str = Column(Text())
    parent_id: int = Column(Integer())
    status: str = Column(String(10), default='active')
    date_create: datetime = Column(DateTime(), default=datetime.now())
    date_update: datetime = Column(DateTime(), nullable=True)

    project = relationship("Project", backref="tasks", uselist=False)

    def __repr__(self):
        return f"db_id - {self.task_id}, ws_id - {self.task_ws_id}, path - {self.task_path}," \
               f" project_id - {self.project_id}, name - {self.task_name}, status - {self.status}"

    def full_name(self):
        return f"{self.project.project_label} | {self.task_name}"

    def complete_task(self):
        Changes.new(self.__tablename__, 'status', self.status, "done")
        self.status = "done"
        self.date_update = datetime.now()
        session.commit()

    def reactivate_task(self):
        Changes.new(self.__tablename__, 'status', self.status, "active")
        self.status = "active"
        self.date_update = datetime.now()
        session.commit()

    def rename_task(self, new_name: str):
        Changes.new(self.__tablename__, 'task_name', self.task_name, new_name)
        self.task_name = new_name
        self.date_update = datetime.now()
        session.commit()

    @staticmethod
    def new_task(task_name: str, project_id: int, parent_id: int = None) -> None:
        t = Task(task_name=task_name,
                 project_id=project_id,
                 parent_id=parent_id,
                 date_create=datetime.now(),
                 date_update=None,
                 status="active"
                 )
        session.add(t)
        session.commit()

    def update(self, parent_id: int):
        Changes.new(self.__tablename__, 'parent_id', self.parent_id, parent_id)
        self.parent_id = parent_id
        self.status = "active"
        self.date_update = datetime.now()
        session.commit()

    def mark_remove(self):
        Changes.new(self.__tablename__, 'status', self.status, "removed")
        self.status = "removed"
        self.date_update = datetime.now()
        session.commit()

    @staticmethod
    def get_subtasks(parent_task_id: int) -> list["Task"]:
        sub_tasks: list[Task] = session.query(Task).filter(Task.parent_id == parent_task_id).all()
        return sub_tasks

    @staticmethod
    def get_tasks(project_id: int) -> list:
        tasks: list[Task] = session.query(Task) \
            .filter(Task.project_id == project_id, Task.parent_id == None).all()
        return tasks

    @staticmethod
    def get_task(task_id: int):
        try:
            return session.query(Task).filter(Task.task_id == task_id).one()
        except NoResultFound:
            print("Task is not exists")

    @staticmethod
    def get_task_by_ws_id(task_ws_id: str):
        try:
            return session.query(Task).filter(Task.task_ws_id == task_ws_id).one()
        except NoResultFound:
            print("Task is not exists")


class Bookmark(Base):
    __tablename__ = 'bookmarks'
    Base.metadata = metadata
    bookmark_id: int = Column(Integer(), primary_key=True, nullable=False)
    task_id: int = Column(Integer(), ForeignKey('tasks.task_id'), nullable=False)
    bookmark_name: str = Column(Text(), nullable=False)
    task: Task = relationship("Task", uselist=False)

    def __repr__(self):
        return f"bookmark_id - {self.bookmark_id} | bookmark_name - {self.bookmark_name} | " \
               f"task_id - {self.task_id}"

    @staticmethod
    def get_bookmark(task_id: int):
        try:
            task: Task = Task.get_task(task_id)
            return session.query(Bookmark).filter(Bookmark.task_id == task.task_id).one()
        except NoResultFound:
            task: Task = Task.get_task(task_id)
            bookmark_name = f"{task.task_name} | {str(task.project)}"
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

user_project = Table("user_project", Base.metadata,
                     Column("user_id", Integer(), ForeignKey("users.user_id"), nullable=False),
                     Column("project_id", Integer(), ForeignKey("projects.project_id"), nullable=False)
                     )


class Status(Base):
    __tablename__ = "statuses"
    Base.metadata = metadata
    status_id: int = Column(Integer(), primary_key=True, nullable=False)
    status_name: str = Column(String(20), nullable=False)
    status_ru_name: str = Column(String(30))

    def __repr__(self):
        return f'{self.status_ru_name}'

    @staticmethod
    def get_users(status: str) -> list:
        searched_status: Status = Status.get_status(status)
        return [i for i in session.query(User).all() if searched_status in i.statuses]

    @staticmethod
    def get_users_telegram_id(status: str) -> list[int]:
        searched_status: Status = Status.get_status(status)
        return [i[0] for i in session.query(User.telegram_id).all() if searched_status in i.statuses]

    @staticmethod
    def get_status(status_name: str):
        return session.query(Status).filter(Status.status_name == status_name).one()


class User(Base):
    __tablename__ = 'users'
    Base.metadata = metadata
    telegram_id: Optional[int] = Column(Integer())
    user_id: int = Column(Integer(), primary_key=True, nullable=False)
    ws_id: Optional[int] = Column(Integer(), nullable=True)
    email: str = Column(String(30))
    first_name: str = Column(String(50))
    last_name: str = Column(String(50))
    date_of_input: datetime = Column(DateTime, nullable=True, default=None)
    selected_task: Optional[int] = Column(Integer(), ForeignKey("tasks.task_id"), nullable=True, unique=False)
    notification_status: bool = Column(Boolean, default=True)
    notification_time: time = Column(DateTime, default='')
    remind_notification: Optional[datetime] = Column(DateTime)
    hashed_password: Optional[str] = Column(String(), default=None)
    user_image: Optional[bytes] = Column(LargeBinary(), nullable=True)
    date_create: datetime = Column(DateTime(), default=datetime.now())
    date_update: datetime = Column(DateTime(), nullable=True)

    default_task: Task = relationship("Task", uselist=False)

    projects: list[Project] = relationship("Project", secondary=user_project, backref="users")
    statuses: list[Status] = relationship("Status", secondary=user_status)
    bookmarks: list[Bookmark] = relationship("Bookmark", secondary=user_bookmark)

    def __repr__(self):
        return f"\n{self.statuses} {self.full_name()}, id{self.user_id} с почтой {self.email}\nЗадача по умолчанию: id" \
               f"{self.default_task.task_ws_id if self.default_task else 'NONE'} - " \
               f"{self.default_task.task_name if self.default_task else ''} " \
               f"на дату {self.date_of_input}\n" \
               f"Статус уведомлений - {self.notification_status} на {self.notification_time} или " \
               f"{self.remind_notification}"

    def is_blocked(self) -> bool:
        return True if "blocked" in self.get_status() else False

    def has_access(self) -> bool:
        return True if 'user' in self.get_status() and not self.is_blocked() else False

    def is_manager(self) -> bool:
        return True if "manager" in self.get_status() and not self.is_blocked() else False

    def is_top_manager(self) -> bool:
        return True if "topmanager" in self.get_status() and not self.is_blocked() else False

    def is_admin(self) -> bool:
        return True if "admin" in self.get_status() and not self.is_blocked() else False

    def get_status(self) -> list[str]:
        return [i.status_name for i in self.statuses]

    def get_date(self, ru: bool = False) -> str:
        if self.date_of_input is None:
            if ru:
                return "сегодня"
            return "today"
        return self.date_of_input.strftime("%d.%m.%Y")

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
        admin_users: list[User] = Status.get_users("admin")
        admin_id: int = admin_users[0].telegram_id
        return admin_id

    def change_date(self, new_date: str):
        if new_date == "сегодня" or new_date == "today":
            new_date = None
        else:
            new_date = datetime.strptime(new_date, "%d.%m.%Y")
        Changes.new(self.__tablename__, 'date_of_input', self.date_of_input, new_date)
        self.date_update = datetime.now()
        self.date_of_input = new_date
        session.commit()

    def change_mail(self, new_email: str):
        Changes.new(self.__tablename__, 'email', self.email, new_email)
        self.email = new_email
        self.date_update = datetime.now()
        session.commit()

    def change_status(self, new_status: str, old_status: str):
        self.remove_status(old_status)
        self.add_status(new_status)

    def add_status(self, status_name: str):
        Changes.new(self.__tablename__, 'add_role', None, status_name)
        status: Status = Status.get_status(status_name)
        self.statuses.append(status)
        self.date_update = datetime.now()
        session.add(self)
        session.commit()

    def remove_status(self, status_name: str):
        Changes.new(self.__tablename__, 'remove_role', None, status_name)
        status: Status = Status.get_status(status_name)
        self.statuses.remove(status)
        self.date_update = datetime.now()
        session.add(self)
        session.commit()

    def add_project(self, project: Project):
        Changes.new(self.__tablename__, 'new_project', None, project.project_id)
        self.projects.append(project)
        self.date_update = datetime.now()
        session.commit()

    def remove_project(self, project: Project):
        Changes.new(self.__tablename__, 'remove_project', None, project.project_id)
        self.projects.remove(project)
        self.date_update = datetime.now()
        session.commit()

    def change_default_task(self, new_default_task_id: int) -> str:
        Changes.new(self.__tablename__, 'selected_task', self.selected_task, new_default_task_id)
        self.selected_task = new_default_task_id
        self.date_update = datetime.now()
        session.commit()
        return '\n'.join(['Выбранная задача:', self.default_task.full_name()])

    def toggle_notification_status(self):
        Changes.new(self.__tablename__, 'notification_status', self.notification_status, not self.notification_status)
        self.notification_status = not self.notification_status
        self.date_update = datetime.now()
        session.commit()

    def set_notification_time(self, new_time: datetime.time):
        Changes.new(self.__tablename__, 'notification_time', self.notification_time.isoformat(), new_time.isoformat())
        self.notification_time = new_time
        self.date_update = datetime.now()
        session.commit()

    def get_remind_notification_time(self) -> str:
        if isinstance(self.remind_notification, type(None)):
            return 'XX:XX'
        return self.remind_notification.strftime("%H:%M")

    def set_remind_time(self, new_time: Optional[datetime]):
        Changes.new(self.__tablename__, 'remind_notification',
                    self.remind_notification.isoformat(), new_time.isoformat())
        self.remind_notification = new_time
        self.date_update = datetime.now()
        session.commit()

    def set_telegram_id(self, telegram_id: int):
        Changes.new(self.__tablename__, 'telegram_id', self.telegram_id, telegram_id)
        self.telegram_id = telegram_id
        self.date_update = datetime.now()
        session.commit()

    def add_bookmark(self, bookmark: Bookmark):
        Changes.new(self.__tablename__, 'add_bookmark', None, bookmark.bookmark_id)
        self.bookmarks.append(bookmark)
        self.date_update = datetime.now()
        session.add(self)
        session.commit()

    def remove_bookmark(self, bookmark: Bookmark):
        Changes.new(self.__tablename__, 'remove_bookmark', None, bookmark.bookmark_id)
        self.bookmarks.remove(bookmark)
        self.date_update = datetime.now()
        session.commit()

    def remove_self(self):
        session.delete(self)
        session.commit()

    @staticmethod
    def new_user(telegram_id: int, *args):
        first_name, last_name = args
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name if last_name else "Snow",
            email=None,
            date_of_input=None,
            selected_task=None,
            notification_status=True,
            notification_time=time(hour=18, minute=30),
            remind_notification=None,
            date_create=datetime.now(),
            date_update=None,
        )
        session.add(user)
        session.commit()
        new_user: User = User.get_user_by_telegram_id(telegram_id)
        wait_status: Status = Status.get_status('wait')
        new_user.statuses.append(wait_status)
        session.add(new_user)
        session.commit()
        return new_user

    @staticmethod
    def get_user(user_id: int):
        return session.query(User).filter(User.user_id == user_id).one()

    @staticmethod
    def get_user_by_telegram_id(user_id: int):
        return session.query(User).filter(User.telegram_id == user_id).one()

    @staticmethod
    def get_user_by_email(user_email: str):
        return session.query(User).filter(User.email == user_email).first()

    @staticmethod
    def get_user_by_ws_id(user_ws_id: str):
        return session.query(User).filter(User.ws_id == user_ws_id).one()

    @classmethod
    def get_all_users(cls):
        q: list[User] = session.query(User).all()  # .user_id, User.first_name, User.last_name, User.__status
        return q

    @staticmethod
    def get_empty_email() -> list[str]:
        emails: list[str] = session.query(User.email).filter(User.email != None, User.telegram_id == None).all()
        # print(session.query(User.email).filter(User.email != None, User.telegram_id == None).all())
        return [i[0] for i in emails]

    def set_hashed_password(self, hashed_password: Optional[str]):
        Changes.new(self.__tablename__, 'add_password', None, 'new_password')
        self.hashed_password = hashed_password
        session.add(self)
        session.commit()

    def set_image(self, image: bytes):
        Changes.new(self.__tablename__, 'add_image', None, 'new_image')
        self.user_image = image
        self.date_update = datetime.now()
        session.add(self)
        session.commit()


# class UserBookmark(Base):
#     __tablename__ = 'user_bookmark'
#     ub_id = Column(Integer(), primary_key=True, nullable=False)
#     user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
#     bookmark_id = Column(Integer(), ForeignKey('bookmarks.bookmark_id'), nullable=False)


class Comment(Base):
    __tablename__ = 'comments'
    Base.metadata = metadata

    comment_ws_id = Column(Integer(), nullable=True)
    comment_id = Column(Integer(), primary_key=True, nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'))
    task_id = Column(Integer(), ForeignKey('tasks.task_id'))
    time = Column(Interval())
    comment_text = Column(Text())
    date = Column(Date)
    via_bot = Column(Boolean)
    date_create: datetime = Column(DateTime(), default=datetime.now())
    date_update: datetime = Column(DateTime(), nullable=True)

    user: User = relationship("User", uselist=False, backref="comments")
    task: Task = relationship("Task", backref="comments")

    def __repr__(self):
        return f"comment_id - {self.comment_id}, user_id - {self.user_id}, task_id - {self.task_id}," \
               f" via_bot - {self.via_bot}, date - {self.date}, time - {self.time}, text - {self.comment_text}"

    @staticmethod
    def add_comment_in_db(user_id: int, task_id: int,
                          comment_time: str, text: str, comment_date: str, via_bot: bool = True):
        comment = Comment(
            user_id=user_id,
            task_id=task_id,
            time=comment_time,
            comment_text=text,
            date=reformat_date(comment_date),
            via_bot=via_bot,
            date_create=datetime.now(),
            date_update=None,
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


class Changes(Base):
    __tablename__ = 'changes'
    Base.metadata = metadata
    changes_id: int = Column(Integer(), primary_key=True, nullable=False)
    date_of_changes: datetime = Column(DateTime())
    table_changes: str = Column(String(50))
    column_changes: str = Column(String(50))
    old_values: str = Column(Text())
    new_values: str = Column(Text())

    @staticmethod
    def new(table_name: str,
            column_name: str,
            old: Optional[Union[int, str, datetime, time]],
            new: Optional[Union[int, str, datetime, time]]
            ) -> None:
        if isinstance(old, datetime) or isinstance(old, time):
            old: str = old.isoformat()
        if isinstance(new, datetime) or isinstance(new, time):
            new: str = new.isoformat()

        new = Changes(date_of_changes=datetime.now(),
                      table_changes=table_name,
                      column_changes=column_name,
                      old_values=str(old),
                      new_values=str(new),
                      )
        session.add(new)
        session.commit()


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
