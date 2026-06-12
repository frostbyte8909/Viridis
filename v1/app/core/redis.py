import logging
import os
from typing import Dict
from redis.asyncio import Redis, from_url
from redis.client import Script

from app.config import settings

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self) -> None:
        self.redis: Redis | None = None
        self.scripts: Dict[str, Script] = {}

    async def connect(self) -> None:
        self.redis = from_url(str(settings.redis_url), decode_responses=True)
        await self._load_scripts()
        logger.info("Connected to Redis and loaded Lua scripts")

    async def disconnect(self) -> None:
        if self.redis:
            await self.redis.aclose()  # type: ignore

    async def _load_scripts(self) -> None:
        if not self.redis:
            return


        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        
        try:
            with open(os.path.join(scripts_dir, "token_bucket.lua"), "r") as f:
                self.scripts["token_bucket"] = self.redis.register_script(f.read())
            
            with open(os.path.join(scripts_dir, "sliding_window.lua"), "r") as f:
                self.scripts["sliding_window"] = self.redis.register_script(f.read())
        except Exception as e:
            logger.error(f"Failed to load Lua scripts: {e}")
            raise

    def get_client(self) -> Redis:
        if not self.redis:
            raise RuntimeError("Redis client not initialized")
        return self.redis

    def get_script(self, name: str) -> Script:
        script = self.scripts.get(name)
        if not script:
            raise ValueError(f"Script {name} not found")
        return script

redis_manager = RedisManager()
