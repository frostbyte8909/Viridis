"""add_waf_feature_windows_table

Revision ID: dbb9182c155e
Revises: 9b3c7b334b7c
Create Date: 2026-06-14 01:01:27.195274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dbb9182c155e'
down_revision: Union[str, Sequence[str], None] = '9b3c7b334b7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "waf_feature_windows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_ip", sa.Text(), nullable=False, index=True),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("error_density", sa.Numeric(), nullable=False),
        sa.Column("endpoint_spread", sa.Numeric(), nullable=False),
        sa.Column("method_diversity", sa.Numeric(), nullable=False),
        sa.Column("temporal_variance", sa.Numeric(), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("waf_feature_windows")
