"""change_fkey_for_users_default_task

Revision ID: 386733e2743e
Revises: 8486e7e5b806
Create Date: 2022-03-18 15:33:07.858880

"""
from pprint import pprint

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, update

from app.db.structure_of_db import User

# revision identifiers, used by Alembic.
revision = '386733e2743e'
down_revision = '8486e7e5b806'
branch_labels = None
depends_on = None

conn = op.get_bind()


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    users_default_task_stmt = text(
        r'SELECT users.user_id, tasks.task_id FROM users JOIN tasks ON users.selected_task = tasks.task_path')
    users_default_task = conn.execute(users_default_task_stmt).fetchall()
    pprint(users_default_task)
    op.drop_constraint('users_selected_task_fkey', 'users', type_='foreignkey')
    op.drop_constraint('tasks_task_path_key', 'tasks', type_='unique')

    op.drop_column('users', 'selected_task')
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('selected_task', sa.Integer(), nullable=True, unique=False))

    for user_id, task_id in users_default_task:
        stmt = update(User).where(User.user_id == user_id).values(selected_task=task_id)
        conn.execute(stmt)

    op.create_foreign_key('users_selected_task_fkey', 'users', 'tasks', ['selected_task'], ['task_id'])
    # ### end Alembic commands ###


def downgrade():
    pass
    # ### commands auto generated by Alembic - please adjust! ###
    users_default_task_stmt = text(
        r'SELECT users.user_id, tasks.task_path FROM users JOIN tasks ON users.selected_task = tasks.task_id')
    users_default_task = conn.execute(users_default_task_stmt).fetchall()
    pprint(users_default_task)
    op.drop_constraint('users_selected_task_fkey', 'users', type_='foreignkey')
    # op.drop_constraint('tasks_task_path_key', 'tasks', type_='unique')

    op.drop_column('users', 'selected_task')
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('selected_task', sa.String(40), nullable=True, unique=False))

    for user_id, task_path in users_default_task:
        stmt = update(User).where(User.user_id == user_id).values(selected_task=task_path)
        conn.execute(stmt)

    op.create_unique_constraint('tasks_task_path_key', 'tasks', ['task_path'])
    op.create_foreign_key('users_selected_task_fkey', 'users', 'tasks', ['selected_task'], ['task_path'])
    # ### end Alembic commands ###
