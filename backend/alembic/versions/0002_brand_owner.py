"""Every brand belongs to a user (products and ads belong to a user through their brand).

Brands made before accounts existed are given to the oldest user. If there are such brands
and no user yet, the migration stops with a message instead of guessing or deleting data.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("brands") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    conn = op.get_bind()
    if conn.execute(sa.text("select count(*) from brands")).scalar():
        first_user = conn.execute(sa.text("select min(id) from users")).scalar()
        if first_user is None:
            raise RuntimeError(
                "There are brands but no users to own them. Sign up once with the old schema "
                "(migrate to 0001, create an account), or delete the development database, "
                "then run the migration again."
            )
        conn.execute(sa.text("update brands set user_id = :u"), {"u": first_user})

    with op.batch_alter_table("brands") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key(
            "fk_brands_user_id_users", "users", ["user_id"], ["id"], ondelete="RESTRICT"
        )
        batch.create_index("ix_brands_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("brands") as batch:
        batch.drop_index("ix_brands_user_id")
        batch.drop_constraint("fk_brands_user_id_users", type_="foreignkey")
        batch.drop_column("user_id")
