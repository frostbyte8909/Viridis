from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="tenant")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(Text, nullable=False)
    requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    burst_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    burst_refill_rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")


class EndpointWeight(Base):
    __tablename__ = "endpoint_weights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    path_pattern: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Numeric, default=1.0, server_default="1.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Override(Base):
    __tablename__ = "overrides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    override_type: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issued_by: Mapped[str] = mapped_column(Text, nullable=False)
    nonce: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), server_default=text("gen_random_uuid()"), nullable=False)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    endpoint_path: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_consumed: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    tokens_remaining: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    processing_ms: Mapped[float] = mapped_column(Numeric, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, server_default=func.now(), nullable=False)


class UsageRollup(Base):
    __tablename__ = "usage_rollups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    api_key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("api_keys.id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    allowed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    throttled: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    denied: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    avg_processing_ms: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
