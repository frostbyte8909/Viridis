import time
import logging
import asyncio

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_state_change = 0.0
        self.lock = asyncio.Lock()

    async def record_success(self) -> None:
        async with self.lock:
            self.failure_count = 0
            self.state = "CLOSED"

    async def record_failure(self) -> None:
        async with self.lock:
            self.failure_count += 1
            if self.state == "HALF-OPEN" or self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self.last_state_change = time.time()
                logger.error(f"Circuit breaker tripped to OPEN. DB queries suspended for {self.recovery_timeout}s.")

    async def allow_request(self) -> bool:
        async with self.lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if time.time() - self.last_state_change > self.recovery_timeout:
                    self.state = "HALF-OPEN"
                    logger.info("Circuit breaker entered HALF-OPEN state. Testing DB connection.")
                    return True
                return False
            if self.state == "HALF-OPEN":
                return False
            return True

db_circuit_breaker = CircuitBreaker()
