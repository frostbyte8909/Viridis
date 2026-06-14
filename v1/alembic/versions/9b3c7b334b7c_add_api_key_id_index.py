"""add_api_key_id_index

Revision ID: 9b3c7b334b7c
Revises: 
Create Date: 2026-06-14 00:51:00.709891

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9b3c7b334b7c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("idx_audit_log_api_key_id", "audit_log", ["api_key_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_audit_log_api_key_id", "audit_log")
