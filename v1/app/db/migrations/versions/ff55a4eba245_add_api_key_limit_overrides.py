"""add_api_key_limit_overrides

Revision ID: ff55a4eba245
Revises: ee44a4eba244
Create Date: 2026-06-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff55a4eba245'
down_revision: Union[str, Sequence[str], None] = 'ee44a4eba244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('api_key_limit_overrides',
    sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('api_key_id', sa.UUID(as_uuid=True), nullable=False),
    sa.Column('requests_per_minute', sa.Integer(), nullable=True),
    sa.Column('burst_capacity', sa.Integer(), nullable=True),
    sa.Column('burst_refill_rate', sa.Numeric(), nullable=True),
    sa.Column('max_concurrency', sa.Integer(), nullable=True),
    sa.Column('cooldown_seconds', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('api_key_id')
    )


def downgrade() -> None:
    op.drop_table('api_key_limit_overrides')
