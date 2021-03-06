"""add user_projects and add users.ws_id

Revision ID: 4c9dbd6d8dcc
Revises: 49df0b654370
Create Date: 2022-03-21 14:42:12.263686

"""
from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session


# revision identifiers, used by Alembic.
revision = '4c9dbd6d8dcc'
down_revision = '49df0b654370'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_project',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], )
    )
    op.alter_column('comments', 'comment_ws_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tasks', 'task_ws_id',
               existing_type=sa.VARCHAR(length=15),
               nullable=True)
    op.alter_column('tasks', 'task_path',
               existing_type=sa.VARCHAR(length=40),
               nullable=True)
    op.alter_column('tasks', 'project_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('users', sa.Column('ws_id', sa.Integer(), nullable=True))
    op.alter_column('users', 'telegram_id',
               existing_type=sa.INTEGER(),
               nullable=True,
               existing_server_default=sa.text("nextval('users_user_id_seq'::regclass)"))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'telegram_id',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text("nextval('users_user_id_seq'::regclass)"))
    op.drop_column('users', 'ws_id')
    op.alter_column('tasks', 'project_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tasks', 'task_path',
               existing_type=sa.VARCHAR(length=40),
               nullable=False)
    op.alter_column('tasks', 'task_ws_id',
               existing_type=sa.VARCHAR(length=15),
               nullable=False)
    op.alter_column('comments', 'comment_ws_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_table('user_project')
    # ### end Alembic commands ###
