"""Concurrency tests for TokenBucketRateLimiter."""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loofi-fedora-tweaks"))

from utils.rate_limiter import TokenBucketRateLimiter


def test_wait_respects_timeout_boundary():
    limiter = TokenBucketRateLimiter(rate=0.0, capacity=0)

    start = time.monotonic()
    ok = limiter.wait(tokens=1, timeout=0.2)
    elapsed = time.monotonic() - start

    assert ok is False
    assert elapsed >= 0.18
    assert elapsed < 0.5


def test_parallel_waits_complete_without_spin_errors():
    limiter = TokenBucketRateLimiter(rate=20.0, capacity=2)
    results = []
    lock = threading.Lock()

    def _worker():
        acquired = limiter.wait(tokens=1, timeout=1.0)
        with lock:
            results.append(acquired)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2.0)

    assert len(results) == 8
    assert all(isinstance(item, bool) for item in results)
    assert any(results)


def test_wait_immediate_when_tokens_already_available():
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=3)
    ok = limiter.wait(tokens=1, timeout=0.1)
    assert ok is True


def test_available_tokens_is_bounded_by_capacity():
    limiter = TokenBucketRateLimiter(rate=1000.0, capacity=2)
    time.sleep(0.01)
    tokens = limiter.available_tokens

    assert tokens <= 2
    assert tokens >= 0
