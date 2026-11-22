"""Admin role, suspended accounts and the activity log.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("role", sa.String(10), nullable=False, server_default="user"))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("detail", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_activity_log_event", "activity_log", ["event"])
    op.create_index("ix_activity_log_created_at", "activity_log", ["created_at"])
    op.create_index("ix_activity_log_user_created", "activity_log", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("activity_log")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_active")
        batch.drop_column("role")
