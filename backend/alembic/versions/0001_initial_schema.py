"""Initial schema: users, sessions, brands, products, ads, verification reports and checks.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=20)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("business_name", sa.String(200)),
        sa.Column("phone", sa.String(30)),
        sa.Column("language", sa.String(5), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "brands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("primary_colors", sa.JSON(), nullable=False),
        sa.Column("secondary_colors", sa.JSON(), nullable=False),
        sa.Column("fonts", sa.JSON(), nullable=False),
        sa.Column("logo_path", sa.String(500)),
        sa.Column("tone_notes", sa.Text()),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_brands_name", "brands", ["name"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("original_price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("specs", sa.JSON(), nullable=False),
        sa.Column("allowed_claims", sa.JSON(), nullable=False),
        sa.Column("key_features", sa.JSON(), nullable=False),
        sa.Column("image_path", sa.String(500)),
        sa.Column("image_sha256", sa.String(64)),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_products_brand_id", "products", ["brand_id"])

    op.create_table(
        "ads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("headline", sa.String(300)),
        sa.Column("caption", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("template_name", sa.String(100)),
        sa.Column("rendered_image_path", sa.String(500)),
        sa.Column("status", _enum("adstatus", "draft", "needs_fix", "verified", "approved"), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("approved_content_hash", sa.String(64)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_ads_product_id", "ads", ["product_id"])

    op.create_table(
        "verification_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ad_id", sa.Integer(), sa.ForeignKey("ads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_reports_ad_id", "verification_reports", ["ad_id"])

    op.create_table(
        "verification_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "report_id",
            sa.Integer(),
            sa.ForeignKey("verification_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "module",
            _enum("checkmodule", "price", "ocr", "claims", "brand", "integrity", "quality"),
            nullable=False,
        ),
        sa.Column(
            "result", _enum("checkresult", "verified", "issue_found", "cannot_verify"), nullable=False
        ),
        sa.Column("severity", _enum("severity", "critical", "warning", "suggestion")),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text()),
        sa.Column("evidence", sa.JSON()),
    )
    op.create_index("ix_verification_checks_report_id", "verification_checks", ["report_id"])


def downgrade() -> None:
    for table in (
        "verification_checks",
        "verification_reports",
        "ads",
        "products",
        "brands",
        "user_sessions",
        "users",
    ):
        op.drop_table(table)
