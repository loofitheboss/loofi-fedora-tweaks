"""
Token bucket rate limiter for network services.
Part of v13.1 stability update.
"""

import threading
import time


class TokenBucketRateLimiter:
    """Token bucket rate limiter.

    Allows bursts up to `capacity` then limits to `rate` tokens per second.
    Thread-safe.
    """

    def __init__(self, rate: float, capacity: int):
        """Initialize rate limiter.

        Args:
            rate: Tokens added per second.
            capacity: Maximum tokens (burst size).
        """
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._wait_event = threading.Event()

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if allowed, False if rate limited."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_refill = now

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait(self, tokens: int = 1, timeout: float = 5.0) -> bool:
        """Block until tokens are available or timeout expires.

        Args:
            tokens: Number of tokens to acquire.
            timeout: Maximum wait time in seconds.

        Returns:
            True if tokens acquired, False if timed out.
        """
        start_time = time.monotonic()
        deadline = start_time + timeout
        while True:
            if self.acquire(tokens):
                return True

            now = time.monotonic()
            if now >= deadline:
                return False

            with self._lock:
                if self._tokens >= tokens:
                    sleep_time = 0.0
                elif self.rate <= 0:
                    sleep_time = deadline - now
                else:
                    needed = max(0.0, float(tokens) - self._tokens)
                    sleep_time = needed / self.rate

            bounded_sleep = max(0.0, min(0.25, sleep_time, deadline - now))
            self._wait_event.wait(bounded_sleep)

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            return min(self.capacity, self._tokens + elapsed * self.rate)
