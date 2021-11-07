import sqlalchemy
import psycopg2
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, Table, String, Integer, Column, Text, DateTime, Date, Boolean, Numeric, SmallInteger
from sqlalchemy import UniqueConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, ForeignKey, CheckConstraint, \
    values, insert, select, create_engine

from datetime import datetime
engine = sqlalchemy.create_engine("postgresql+psycopg2://postgres:Mig120300SQL@localhost/tele_ws",
                                  echo=True, pool_size=6, max_overflow=10, encoding='latin1')


Base = declarative_base()
metadata = MetaData()


class Project(Base):
    __tablename__ = 'projects'
    project_id = Column(String(15), primary_key=True, nullable=False)
    project_name = Column(Text(), nullable=False)
    project_path = Column(String(40), nullable=False)


class Task(Base):
    __tablename__ = 'tasks'
    task_id = Column(Integer(), primary_key=True, nullable=False)
    task_path = Column(String(40), nullable=False)
    project_id = Column(String(15), ForeignKey('projects.project_id'), nullable=False)
    task_name = Column(Text())
    task_ws_id = Column(String(15), nullable=False)
    
    
class Bookmark(Base):
    __tablename__ = 'bookmarks'
    bookmark_id = Column(Integer(), primary_key=True, nullable=False)
    task_id = Column(Integer(), ForeignKey('tasks.task_id'), nullable=False)
    bookmark_name = Column(Text(), nullable=False)


class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer(), primary_key=True, nullable=False)
    email = Column(String(30))
    first_name = Column(String(50))
    last_name = Column(String(50))
    date_of_input = Column(String(15))
    status = Column(String(20), nullable=False)


class UserBookmark(Base):
    __tablename__ = 'user_bookmark'
    ub_id = Column(Integer(), primary_key=True, nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'), nullable=False)
    bookmark_id = Column(Integer(), ForeignKey('bookmarks.bookmark_id'), nullable=False)
    

class Comment(Base):
    __tablename__ = 'comments'
    comment_id = Column(Integer(), primary_key=True, nullable=False)
    user_id = Column(Integer(), ForeignKey('users.user_id'))
    task_id = Column(Integer(), ForeignKey('tasks.task_id'))
    time = Column(String(10))
    comment_text = Column(Text())
    date = Column(Date())


Base.metadata.create_all(engine)
