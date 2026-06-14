from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client.exposition import generate_latest, CONTENT_TYPE_LATEST
import time

# Prometheus registries
registry = CollectorRegistry()

# Counters
viridis_requests_total = Counter(
    "viridis_requests_total",
    "Total number of requests processed by Viridis",
    labelnames=["method", "endpoint", "status"],
    registry=registry,
)

viridis_blocks_total = Counter(
    "viridis_blocks_total",
    "Total number of blocked requests",
    labelnames=["reason"],  # ML_WAF, L7_SQLI, L7_XSS, L7_PII_LEAKAGE, QUOTA, CONCURRENCY
    registry=registry,
)

# Histogram (latency p99 tracking)
viridis_processing_latency_seconds = Histogram(
    "viridis_processing_latency_seconds",
    "Processing latency for /v1/admit endpoint",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],  # 1ms to 1s
    registry=registry,
)

# Gauges
viridis_active_concurrency_slots = Gauge(
    "viridis_active_concurrency_slots",
    "Number of active concurrency slots",
    registry=registry,
)

viridis_waf_blocked_ips = Gauge(
    "viridis_waf_blocked_ips",
    "Number of currently blocked IPs by ML WAF",
    registry=registry,
)

# Emit block metric
def emit_block(reason: str):
    """Emit block counter."""
    viridis_blocks_total.labels(reason=reason).inc()
