"""Admin sign-in with a secret word.

* users.admin_secret_hash: scrypt hash of the admin's secret word (empty for normal users)
* user_sessions.admin_verified: true only for sessions made on the admin sign-in page

Existing admin sessions become unverified, so admins sign in again on the admin page.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("admin_secret_hash", sa.String(300), nullable=True))
    with op.batch_alter_table("user_sessions") as batch:
        batch.add_column(
            sa.Column("admin_verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("user_sessions") as batch:
        batch.drop_column("admin_verified")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("admin_secret_hash")
