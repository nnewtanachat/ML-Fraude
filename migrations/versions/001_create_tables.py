"""Create initial tables and users

Revision ID: 001
Revises: None
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_amount", sa.Float()),
        sa.Column("hour_of_day", sa.Float()),
        sa.Column("is_weekend", sa.Boolean()),
        sa.Column("num_items", sa.Integer()),
        sa.Column("customer_age", sa.Float()),
        sa.Column("prev_transactions", sa.Float()),
        sa.Column("distance_from_home", sa.Float()),
        sa.Column("device_type", sa.Integer()),
        sa.Column("network_quality", sa.Float()),
        sa.Column("is_first_transaction", sa.Boolean()),
        sa.Column("store_type", sa.Integer()),
        sa.Column("velocity_score", sa.Float()),
        sa.Column("is_fraud", sa.Integer(), nullable=False),
    )

    # Create predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("predicted_fraud", sa.Boolean(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index("idx_transactions_is_fraud", "transactions", ["is_fraud"])
    op.create_index("idx_predictions_transaction_id", "predictions", ["transaction_id"])

    # Create users with least privilege
    op.execute("""
        DO $$ BEGIN
            CREATE USER api_user WITH PASSWORD 'CHANGE_ME_API';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        GRANT SELECT ON transactions TO api_user;
        GRANT SELECT, INSERT ON predictions TO api_user;
        GRANT USAGE, SELECT ON SEQUENCE predictions_id_seq TO api_user;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE USER scorer_user WITH PASSWORD 'CHANGE_ME_SCORER';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        GRANT SELECT ON transactions TO scorer_user;
        GRANT SELECT, INSERT ON predictions TO scorer_user;
        GRANT USAGE, SELECT ON SEQUENCE predictions_id_seq TO scorer_user;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE USER analyst WITH PASSWORD 'CHANGE_ME_ANALYST';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO analyst;
    """)


def downgrade() -> None:
    op.execute("DROP USER IF EXISTS analyst;")
    op.execute("DROP USER IF EXISTS scorer_user;")
    op.execute("DROP USER IF EXISTS api_user;")
    op.drop_index("idx_predictions_transaction_id")
    op.drop_index("idx_transactions_is_fraud")
    op.drop_table("predictions")
    op.drop_table("transactions")
