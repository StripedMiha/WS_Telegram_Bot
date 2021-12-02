from datetime import date, datetime

from app.db.structure_of_db import Comment, Project, Task, User, Bookmark, UserBookmark
from app.auth import _get_session, TUser


def current_month_stat():
    now_month = datetime.now()
    print(now_month)
    first_day_of_months = 0

current_month_stat()