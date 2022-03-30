"""projects nullable

Revision ID: 82ecefc45915
Revises: 92b621266fa8
Create Date: 2022-03-30 16:31:06.828225

"""
from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session


# revision identifiers, used by Alembic.
revision = '82ecefc45915'
down_revision = '92b621266fa8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('projects', 'project_ws_id',
               existing_type=sa.VARCHAR(length=15),
               nullable=True)
    op.alter_column('projects', 'project_path',
               existing_type=sa.VARCHAR(length=40),
               nullable=True)
    op.alter_column('projects', 'project_status',
               existing_type=sa.VARCHAR(length=15),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('projects', 'project_status',
               existing_type=sa.VARCHAR(length=15),
               nullable=True)
    op.alter_column('projects', 'project_path',
               existing_type=sa.VARCHAR(length=40),
               nullable=False)
    op.alter_column('projects', 'project_ws_id',
               existing_type=sa.VARCHAR(length=15),
               nullable=False)
    # ### end Alembic commands ###
