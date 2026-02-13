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

    def _refill_locked(self, now: float) -> None:
        """Refill token bucket. Caller must hold _lock."""
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens. Returns True if allowed, False if rate limited."""
        with self._lock:
            now = time.monotonic()
            self._refill_locked(now)

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
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            with self._lock:
                now = time.monotonic()
                self._refill_locked(now)

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                remaining = deadline - now
                if remaining <= 0:
                    return False

                if self.rate <= 0:
                    sleep_time = remaining
                else:
                    needed_tokens = max(0.0, float(tokens) - self._tokens)
                    sleep_time = needed_tokens / self.rate

            bounded_sleep = max(0.0, min(0.25, sleep_time, remaining))
            time.sleep(bounded_sleep)

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens."""
        with self._lock:
            now = time.monotonic()
            self._refill_locked(now)
            return self._tokens
