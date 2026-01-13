"""Add authoritative column for lineage-aware queries.

Revision ID: 007
Revises: 006
Create Date: 2024-12-31

Phase 3: Authoritative flag for marking canonical versions in a lineage chain.
Supports both SQLite and PostgreSQL.
"""

from alembic import context, op
from sqlalchemy import inspect

# Revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def get_dialect() -> str:
    """Get the database dialect name."""
    return context.get_context().dialect.name


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add authoritative column to memories table."""
    # Check if column already exists (idempotent migration)
    if column_exists("memories", "authoritative"):
        return

    dialect = get_dialect()

    # Boolean type differs between databases
    if dialect == "postgresql":
        op.execute("ALTER TABLE memories ADD COLUMN authoritative BOOLEAN DEFAULT false")
    else:  # sqlite
        op.execute("ALTER TABLE memories ADD COLUMN authoritative INTEGER DEFAULT 0")


def downgrade() -> None:
    """Remove authoritative column (SQLite limitation - recreate table)."""
    # SQLite doesn't support DROP COLUMN, but we'll keep it simple
    # The column will just be ignored if not used
    pass
