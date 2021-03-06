"""change task_parent_id to task_id from task_ws_id

Revision ID: 49468fded71c
Revises: 0c7340e37708
Create Date: 2022-03-21 16:34:57.175729

"""
from pprint import pprint

from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session, Task

# revision identifiers, used by Alembic.
revision = '49468fded71c'
down_revision = '0c7340e37708'
branch_labels = None
depends_on = None

conn = op.get_bind()


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    get_parents_stmt = sa.select(Task.task_id, Task.parent_id).where(Task.parent_id > 0)
    t = conn.execute(get_parents_stmt).fetchall()
    tasks_parents: set = {i[1] for i in t}

    all_tasks_ws_id = sa.select(Task.task_ws_id)
    all_tasks_ws_id: set = {i[0] for i in conn.execute(all_tasks_ws_id).fetchall()}

    tasks = all_tasks_ws_id - (all_tasks_ws_id - tasks_parents)

    parents = {}
    for task_ws_id in tasks:
        stmt = sa.select(Task.task_id).where(Task.task_ws_id == task_ws_id)
        parents[task_ws_id] = conn.execute(stmt).fetchone()[0]

    for task_id, parent_id in t:
        if parent_id in tasks:
            stmt = sa.update(Task).where(Task.task_id == task_id).values(parent_id=parents[parent_id])
            conn.execute(stmt)
        else:
            stmt = sa.update(Task).where(Task.task_id == task_id).values(parent_id=None)
            conn.execute(stmt)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    tasks_parents_stmt = sa.select(Task.task_id, Task.task_path).where(Task.parent_id > 0)
    tasks_parents = conn.execute(tasks_parents_stmt).fetchall()

    all_tasks_ws_id = sa.select(Task.task_ws_id)
    all_tasks_ws_id: set = {i[0] for i in conn.execute(all_tasks_ws_id).fetchall()}

    for task_id, task_path in tasks_parents:
        prev = int(task_path.strip("/").split("/")[-2])
        if prev in all_tasks_ws_id:
            stmt = sa.update(Task).where(Task.task_id == task_id).values(parent_id=prev)
            conn.execute(stmt)

    # for task_id, task_ws_id in tasks_parents:
    #     stmt = sa.update(Task).where(Task.task_id == task_id).values(parent_id=task_ws_id)
    #     conn.execute(stmt)
    # ### end Alembic commands ###
