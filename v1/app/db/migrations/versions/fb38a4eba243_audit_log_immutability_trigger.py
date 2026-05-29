"""audit_log_immutability_trigger

Revision ID: fb38a4eba243
Revises: 
Create Date: 2026-06-10 17:14:00.474621

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'fb38a4eba243'
down_revision: Union[str, Sequence[str], None] = 'cb224e493485'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Trigger to prevent updates or deletes on audit_log
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log is append-only. UPDATE and DELETE are strictly forbidden.';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_prevent_audit_log_mod
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_log_mod ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification();")
