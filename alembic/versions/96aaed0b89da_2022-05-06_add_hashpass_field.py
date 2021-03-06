"""add hashpass field

Revision ID: 96aaed0b89da
Revises: 7fd18769c9e7
Create Date: 2022-05-06 13:10:47.601082

"""
from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '96aaed0b89da'
down_revision = '7fd18769c9e7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('hashed_password', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'hashed_password')
    # ### end Alembic commands ###
