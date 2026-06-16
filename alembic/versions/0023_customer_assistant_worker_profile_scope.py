"""customer assistant worker profile scope

Revision ID: 0023_customer_assistant_worker_profile_scope
Revises: 0022_customer_assistant_worker_profiles
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0023_customer_assistant_worker_profile_scope"
down_revision: str | None = "0022_customer_assistant_worker_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("customer_assistant_worker_profile")}
    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("customer_assistant_worker_profile")}
    indexes = {index["name"] for index in inspector.get_indexes("customer_assistant_worker_profile")}
    needs_tenant = "tenant_id" not in columns
    needs_org = "org_id" not in columns
    needs_drop_old_unique = "idx_customer_assistant_worker_profile_id" in unique_constraints
    needs_new_unique = "idx_customer_assistant_worker_profile_scope_id" not in unique_constraints
    needs_scope_index = "idx_customer_assistant_worker_profile_scope" not in indexes
    if not any((needs_tenant, needs_org, needs_drop_old_unique, needs_new_unique, needs_scope_index)):
        return
    with op.batch_alter_table("customer_assistant_worker_profile") as batch_op:
        if needs_tenant:
            batch_op.add_column(sa.Column("tenant_id", sa.String(120), nullable=False, server_default="local"))
        if needs_org:
            batch_op.add_column(sa.Column("org_id", sa.String(120), nullable=False, server_default="local"))
        if needs_drop_old_unique:
            batch_op.drop_constraint("idx_customer_assistant_worker_profile_id", type_="unique")
        if needs_new_unique:
            batch_op.create_unique_constraint(
                "idx_customer_assistant_worker_profile_scope_id",
                ["tenant_id", "org_id", "profile_id"],
            )
        if needs_scope_index:
            batch_op.create_index("idx_customer_assistant_worker_profile_scope", ["tenant_id", "org_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("customer_assistant_worker_profile")}
    unique_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("customer_assistant_worker_profile")}
    indexes = {index["name"] for index in inspector.get_indexes("customer_assistant_worker_profile")}
    with op.batch_alter_table("customer_assistant_worker_profile") as batch_op:
        if "idx_customer_assistant_worker_profile_scope" in indexes:
            batch_op.drop_index("idx_customer_assistant_worker_profile_scope")
        if "idx_customer_assistant_worker_profile_scope_id" in unique_constraints:
            batch_op.drop_constraint("idx_customer_assistant_worker_profile_scope_id", type_="unique")
        if "idx_customer_assistant_worker_profile_id" not in unique_constraints:
            batch_op.create_unique_constraint("idx_customer_assistant_worker_profile_id", ["profile_id"])
        if "org_id" in columns:
            batch_op.drop_column("org_id")
        if "tenant_id" in columns:
            batch_op.drop_column("tenant_id")
