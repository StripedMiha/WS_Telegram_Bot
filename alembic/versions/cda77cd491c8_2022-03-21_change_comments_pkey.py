"""change_comments_pkey

Revision ID: cda77cd491c8
Revises: 386733e2743e
Create Date: 2022-03-21 11:14:13.996991

"""
from alembic import op
import sqlalchemy as sa

from app.db.structure_of_db import session


# revision identifiers, used by Alembic.
revision = 'cda77cd491c8'
down_revision = '386733e2743e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("comments_pkey", "comments", type_="primary")
    op.alter_column("comments", "comment_id", new_column_name="comment_ws_id")
    with op.batch_alter_table("comments") as batch_op:
        batch_op.add_column(sa.Column("comment_id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False))
    op.create_primary_key("comments_pkey", "comments", ["comment_id"])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.drop_constraint("comments_pkey", "comments", type_="primary")
    op.drop_column("comments", "comment_id")
    op.alter_column("comments", "comment_ws_id", new_column_name="comment_id")
    op.create_primary_key("comments_pkey", "comments", ["comment_id"])

    # ### end Alembic commands ###
