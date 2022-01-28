from sqlalchemy import text

from app.db.structure_of_db import Task, _get_session


def get_task_without_parrents():
    session = _get_session()
    raw = text("SELECT * FROM tasks WHERE parent_id IS NULL")
    tasks = session.execute(raw)
    session.close()
    return [i for i in tasks]


def update_parent(parent, task_path):
    session = _get_session()
    i: Task = session.query(Task).filter(Task.task_path == task_path).one()
    i.parent_id = parent
    session.add(i)
    session.commit()
    session.close()


async def fix_parent(s):
    tasks = get_task_without_parrents()
    for task in tasks:
        path: str = task[1]
        path = path.strip('/')
        parent = path.split('/')[-2]
        update_parent(parent, task[1])
