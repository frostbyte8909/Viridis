import time
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_state_change = 0.0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.error(f"Circuit breaker tripped to OPEN. DB queries suspended for {self.recovery_timeout}s.")

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_state_change > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info("Circuit breaker entered HALF-OPEN state. Testing DB connection.")
                return True
            return False
        return True  # HALF-OPEN lets test requests pass

class CircuitBreakerError(Exception):
    pass

import contextlib

@contextlib.asynccontextmanager
async def execute_with_circuit_breaker(cb: CircuitBreaker):
    if not cb.allow_request():
        raise CircuitBreakerError("Circuit breaker is OPEN. Request denied.")
    try:
        yield
        cb.record_success()
    except Exception as e:
        cb.record_failure()
        raise e

db_circuit_breaker = CircuitBreaker()
