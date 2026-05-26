"""partition_audit_log

Revision ID: ee44a4eba244
Revises: fb38a4eba243
Create Date: 2026-06-12 11:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee44a4eba244'
down_revision: Union[str, Sequence[str], None] = 'fb38a4eba243'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename existing table
    op.execute("ALTER TABLE audit_log RENAME TO audit_log_old;")
    
    # 2. Re-create audit_log with PARTITION BY RANGE
    op.execute("""
    CREATE TABLE audit_log (
        id SERIAL,
        decision_id UUID NOT NULL DEFAULT gen_random_uuid(),
        api_key_id UUID NOT NULL,
        tenant_id UUID NOT NULL,
        endpoint_path TEXT NOT NULL,
        method TEXT NOT NULL,
        decision TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        tokens_consumed NUMERIC,
        tokens_remaining NUMERIC,
        processing_ms NUMERIC NOT NULL,
        client_ip TEXT,
        trace_id TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
        PRIMARY KEY (id, created_at)
    ) PARTITION BY RANGE (created_at);
    """)

    # 3. Create default partition
    op.execute("CREATE TABLE audit_log_default PARTITION OF audit_log DEFAULT;")
    
    # 4. Migrate old data and drop old table
    op.execute("INSERT INTO audit_log (id, decision_id, api_key_id, tenant_id, endpoint_path, method, decision, reason_code, tokens_consumed, tokens_remaining, processing_ms, client_ip, trace_id, created_at) SELECT id, decision_id, api_key_id, tenant_id, endpoint_path, method, decision, reason_code, tokens_consumed, tokens_remaining, processing_ms, client_ip, trace_id, created_at FROM audit_log_old;")
    op.execute("DROP TABLE audit_log_old;")

    # 5. Reapply the immutability trigger to the parent partitioned table
    op.execute("""
    CREATE TRIGGER trg_prevent_audit_log_mod
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
    """)


def downgrade() -> None:
    # 1. Rename partition table
    op.execute("ALTER TABLE audit_log RENAME TO audit_log_partitioned;")
    
    # 2. Recreate original table
    op.execute("""
    CREATE TABLE audit_log (
        id SERIAL PRIMARY KEY,
        decision_id UUID NOT NULL DEFAULT gen_random_uuid(),
        api_key_id UUID NOT NULL,
        tenant_id UUID NOT NULL,
        endpoint_path TEXT NOT NULL,
        method TEXT NOT NULL,
        decision TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        tokens_consumed NUMERIC,
        tokens_remaining NUMERIC,
        processing_ms NUMERIC NOT NULL,
        client_ip TEXT,
        trace_id TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
    );
    """)

    # 3. Copy data back
    op.execute("INSERT INTO audit_log (id, decision_id, api_key_id, tenant_id, endpoint_path, method, decision, reason_code, tokens_consumed, tokens_remaining, processing_ms, client_ip, trace_id, created_at) SELECT id, decision_id, api_key_id, tenant_id, endpoint_path, method, decision, reason_code, tokens_consumed, tokens_remaining, processing_ms, client_ip, trace_id, created_at FROM audit_log_partitioned;")
    
    # 4. Drop partitioned tables
    op.execute("DROP TABLE audit_log_partitioned CASCADE;")
    
    # 5. Reapply trigger
    op.execute("""
    CREATE TRIGGER trg_prevent_audit_log_mod
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
    """)
