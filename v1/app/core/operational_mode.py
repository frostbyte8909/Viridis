from app.core.redis import redis_manager

async def get_operational_mode() -> str:
    """Gets the current operational mode from Redis."""
    r = redis_manager.get_client()
    mode = await r.get("viridis:mode")
    return mode or "normal"

async def set_operational_mode(mode: str) -> None:
    """Sets the operational mode. Valid values: normal, degraded, maintenance"""
    if mode not in ["normal", "degraded", "maintenance"]:
        raise ValueError("Invalid mode")
    r = redis_manager.get_client()
    await r.set("viridis:mode", mode)
