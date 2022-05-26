"""add_object_id_changes

Revision ID: fb3efbfa8d19
Revises: 0268251b90a3
Create Date: 2022-05-26 11:53:48.755611

"""
from alembic import op
import sqlalchemy as sa
from app.db.structure_of_db import session
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fb3efbfa8d19'
down_revision = '0268251b90a3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('changes', sa.Column('id_object', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('changes', 'id_object')
    # ### end Alembic commands ###
