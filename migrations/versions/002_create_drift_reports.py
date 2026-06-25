"""Create drift_reports table

Revision ID: 002
Revises: 001
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drift_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("check_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("data_drift_detected", sa.Boolean(), nullable=False),
        sa.Column("drift_share", sa.Float()),
        sa.Column("n_drifted_columns", sa.Integer()),
        sa.Column("prediction_drift_detected", sa.Boolean()),
        sa.Column("reference_fraud_rate", sa.Float()),
        sa.Column("current_fraud_rate", sa.Float()),
    )


def downgrade() -> None:
    op.drop_table("drift_reports")
