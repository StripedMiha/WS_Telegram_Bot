"""add_project_image

Revision ID: d183981b007b
Revises: 96aaed0b89da
Create Date: 2022-05-11 14:35:34.777775

"""
from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd183981b007b'
down_revision = '96aaed0b89da'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('projects', sa.Column('project_image', sa.LargeBinary(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('projects', 'project_image')
    # ### end Alembic commands ###