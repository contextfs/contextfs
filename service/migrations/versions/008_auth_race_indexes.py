"""Add composite index for auth race condition fix.

Revision ID: 008
Revises: 007
Create Date: 2026-01-27

Adds:
- Composite index on api_keys (user_id, name) for faster session key lookups
  during atomic replacement operations.
"""

from alembic import op
from sqlalchemy import inspect, text

# Revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes("api_keys")
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add composite index for user_id + name on api_keys table."""
    if not index_exists("idx_api_keys_user_name"):
        op.create_index(
            "idx_api_keys_user_name",
            "api_keys",
            ["user_id", "name"],
        )


def downgrade() -> None:
    """Remove the composite index."""
    conn = op.get_bind()
    conn.execute(text("DROP INDEX IF EXISTS idx_api_keys_user_name"))
