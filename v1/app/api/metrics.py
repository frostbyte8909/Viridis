from fastapi import APIRouter
from fastapi.responses import Response
from app.core.metrics import registry, CONTENT_TYPE_LATEST
from prometheus_client.exposition import generate_latest

router = APIRouter(tags=["Metrics"])

@router.get("/metrics")
async def get_metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )
