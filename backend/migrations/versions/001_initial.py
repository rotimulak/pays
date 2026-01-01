"""Initial migration with all tables, constraints, and indexes.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    invoice_status = postgresql.ENUM(
        "pending", "paid", "expired", "cancelled", "refunded",
        name="invoice_status",
        create_type=True,
    )
    transaction_type = postgresql.ENUM(
        "topup", "spend", "refund", "adjustment",
        name="transaction_type",
        create_type=True,
    )
    discount_type = postgresql.ENUM(
        "percent", "fixed",
        name="discount_type",
        create_type=True,
    )

    invoice_status.create(op.get_bind(), checkfirst=True)
    transaction_type.create(op.get_bind(), checkfirst=True)
    discount_type.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False, comment="Telegram user_id"),
        sa.Column("username", sa.String(255), nullable=True, comment="Telegram username"),
        sa.Column("first_name", sa.String(255), nullable=True, comment="User first name"),
        sa.Column("last_name", sa.String(255), nullable=True, comment="User last name"),
        sa.Column("token_balance", sa.Integer(), nullable=False, server_default="0", comment="Token balance"),
        sa.Column("balance_version", sa.Integer(), nullable=False, server_default="0", comment="Version for optimistic locking"),
        sa.Column("subscription_end", sa.DateTime(), nullable=True, comment="Subscription end date"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false", comment="User is blocked"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record creation time"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record update time"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.CheckConstraint("token_balance >= 0", name="ck_users_token_balance_non_negative"),
    )

    # Create tariffs table
    op.create_table(
        "tariffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="Tariff UUID"),
        sa.Column("slug", sa.String(50), nullable=False, comment="URL-friendly identifier"),
        sa.Column("name", sa.String(100), nullable=False, comment="Display name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Tariff description"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, comment="Price in RUB"),
        sa.Column("tokens", sa.Integer(), nullable=False, comment="Number of tokens included"),
        sa.Column("subscription_days", sa.Integer(), nullable=False, server_default="0", comment="Subscription duration in days"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="Display order"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="Tariff is available for purchase"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1", comment="Tariff version for history tracking"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record creation time"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record update time"),
        sa.PrimaryKeyConstraint("id", name="pk_tariffs"),
        sa.UniqueConstraint("slug", name="uq_tariffs_slug"),
        sa.CheckConstraint("price > 0", name="ck_tariffs_price_positive"),
        sa.CheckConstraint("tokens >= 0", name="ck_tariffs_tokens_non_negative"),
        sa.CheckConstraint("subscription_days >= 0", name="ck_tariffs_subscription_days_non_negative"),
    )

    # Create partial index for active tariffs
    op.create_index(
        "idx_tariffs_is_active",
        "tariffs",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # Create promo_codes table
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="Promo code UUID"),
        sa.Column("code", sa.String(50), nullable=False, comment="Promo code string"),
        sa.Column("discount_type", postgresql.ENUM("percent", "fixed", name="discount_type", create_type=False), nullable=False, comment="Type of discount"),
        sa.Column("discount_value", sa.Numeric(10, 2), nullable=False, comment="Discount amount (% or fixed RUB)"),
        sa.Column("max_uses", sa.Integer(), nullable=True, comment="Maximum number of uses (null = unlimited)"),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default="0", comment="Current usage count"),
        sa.Column("valid_from", sa.DateTime(), nullable=False, comment="Start of validity period"),
        sa.Column("valid_until", sa.DateTime(), nullable=True, comment="End of validity period (null = no expiry)"),
        sa.Column("tariff_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Limit to specific tariff (null = all tariffs)"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true", comment="Promo code is usable"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record creation time"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record update time"),
        sa.PrimaryKeyConstraint("id", name="pk_promo_codes"),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], name="fk_promo_codes_tariff_id_tariffs", ondelete="SET NULL"),
        sa.CheckConstraint("discount_value > 0", name="ck_promo_codes_discount_value_positive"),
        sa.CheckConstraint("uses_count >= 0", name="ck_promo_codes_uses_count_non_negative"),
        sa.CheckConstraint("max_uses IS NULL OR max_uses > 0", name="ck_promo_codes_max_uses_positive_or_null"),
    )

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="Invoice UUID"),
        sa.Column("inv_id", sa.BigInteger(), nullable=False, comment="Robokassa invoice ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="User who created the invoice"),
        sa.Column("tariff_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Purchased tariff"),
        sa.Column("promo_code_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Applied promo code"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, comment="Amount to pay after discount"),
        sa.Column("original_amount", sa.Numeric(10, 2), nullable=False, comment="Original amount before discount"),
        sa.Column("tokens", sa.Integer(), nullable=False, comment="Tokens to credit on payment"),
        sa.Column("subscription_days", sa.Integer(), nullable=False, comment="Subscription days to add on payment"),
        sa.Column("status", postgresql.ENUM("pending", "paid", "expired", "cancelled", "refunded", name="invoice_status", create_type=False), nullable=False, server_default="pending", comment="Payment status"),
        sa.Column("idempotency_key", sa.String(255), nullable=False, comment="Idempotency key to prevent duplicates"),
        sa.Column("payment_url", sa.Text(), nullable=True, comment="Payment gateway URL"),
        sa.Column("paid_at", sa.DateTime(), nullable=True, comment="Payment completion time"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="Invoice expiration time"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record creation time"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Record update time"),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
        sa.UniqueConstraint("inv_id", name="uq_invoices_inv_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_invoices_idempotency_key"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_invoices_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], name="fk_invoices_tariff_id_tariffs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["promo_code_id"], ["promo_codes.id"], name="fk_invoices_promo_code_id_promo_codes", ondelete="SET NULL"),
        sa.CheckConstraint("amount > 0", name="ck_invoices_amount_positive"),
    )

    # Create indexes for invoices
    op.create_index("idx_invoices_user_id", "invoices", ["user_id"])
    op.create_index("idx_invoices_status", "invoices", ["status"])
    op.create_index("idx_invoices_idempotency_key", "invoices", ["idempotency_key"])
    op.create_index("idx_invoices_inv_id", "invoices", ["inv_id"])
    op.create_index(
        "idx_invoices_expires_at_pending",
        "invoices",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="Transaction UUID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="User who owns the transaction"),
        sa.Column("type", postgresql.ENUM("topup", "spend", "refund", "adjustment", name="transaction_type", create_type=False), nullable=False, comment="Transaction type"),
        sa.Column("tokens_delta", sa.Integer(), nullable=False, comment="Token change (positive or negative)"),
        sa.Column("balance_after", sa.Integer(), nullable=False, comment="Token balance after transaction"),
        sa.Column("description", sa.Text(), nullable=True, comment="Transaction description"),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Related invoice for topup/refund"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True, comment="Additional transaction data"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Transaction time"),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_transactions_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="fk_transactions_invoice_id_invoices", ondelete="SET NULL"),
    )

    # Create indexes for transactions
    op.create_index("idx_transactions_user_id", "transactions", ["user_id"])
    op.create_index("idx_transactions_created_at", "transactions", ["created_at"])
    op.create_index("idx_transactions_type", "transactions", ["type"])

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, comment="Audit log entry UUID"),
        sa.Column("user_id", sa.BigInteger(), nullable=True, comment="Related user ID (no FK for independence)"),
        sa.Column("action", sa.String(100), nullable=False, comment="Action performed"),
        sa.Column("entity_type", sa.String(50), nullable=False, comment="Entity type affected"),
        sa.Column("entity_id", sa.String(255), nullable=True, comment="Entity ID affected"),
        sa.Column("old_value", postgresql.JSONB(), nullable=True, comment="Previous state"),
        sa.Column("new_value", postgresql.JSONB(), nullable=True, comment="New state"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True, comment="Additional event data"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="Event time"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )

    # Create indexes for audit_logs
    op.create_index("idx_audit_log_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_log_action", "audit_logs", ["action"])
    op.create_index("idx_audit_log_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table("audit_logs")
    op.drop_table("transactions")
    op.drop_table("invoices")
    op.drop_table("promo_codes")
    op.drop_table("tariffs")
    op.drop_table("users")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS invoice_status")
    op.execute("DROP TYPE IF EXISTS transaction_type")
    op.execute("DROP TYPE IF EXISTS discount_type")
