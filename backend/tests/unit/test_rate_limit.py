import os
from uuid import uuid4

import pytest

from app.core.rate_limit import LoginRateLimiter, MemoryCounterStore, RedisCounterStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _limiter(clock, max_failures=3, ip_max_failures=5, window_seconds=60):
    return LoginRateLimiter(
        MemoryCounterStore(clock),
        max_failures=max_failures,
        ip_max_failures=ip_max_failures,
        window_seconds=window_seconds,
    )


def test_allowed_until_the_threshold_then_blocked_with_remaining_time():
    clock = Clock()
    limiter = _limiter(clock)

    for _ in range(2):
        limiter.record_failure("1.1.1.1", "alice")
    assert limiter.retry_after("1.1.1.1", "alice") == 0

    limiter.record_failure("1.1.1.1", "alice")
    assert limiter.retry_after("1.1.1.1", "alice") == 60
    clock.now += 25
    assert limiter.retry_after("1.1.1.1", "alice") == 35


def test_block_expires_with_the_window():
    clock = Clock()
    limiter = _limiter(clock)
    for _ in range(3):
        limiter.record_failure("1.1.1.1", "alice")

    clock.now += 61

    assert limiter.retry_after("1.1.1.1", "alice") == 0


def test_window_does_not_slide_forward_on_each_failure():
    clock = Clock()
    limiter = _limiter(clock)
    limiter.record_failure("1.1.1.1", "alice")
    clock.now += 50
    limiter.record_failure("1.1.1.1", "alice")
    limiter.record_failure("1.1.1.1", "alice")

    assert limiter.retry_after("1.1.1.1", "alice") == 10


def test_counters_are_separate_per_ip_and_per_username():
    limiter = _limiter(Clock())
    for _ in range(3):
        limiter.record_failure("1.1.1.1", "alice")

    assert limiter.retry_after("1.1.1.1", "alice") > 0
    assert limiter.retry_after("1.1.1.1", "bob") == 0
    assert limiter.retry_after("2.2.2.2", "alice") == 0


def test_reset_clears_only_the_ip_username_pair():
    limiter = _limiter(Clock(), ip_max_failures=4)
    for _ in range(3):
        limiter.record_failure("1.1.1.1", "alice")
    limiter.record_failure("1.1.1.1", "bob")

    limiter.reset("1.1.1.1", "alice")

    assert limiter.retry_after("1.1.1.1", "alice") > 0, "bộ đếm theo IP vẫn đạt ngưỡng 4"
    assert limiter.retry_after("1.1.1.1", "bob") > 0


@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="Cần TEST_REDIS_URL trỏ tới Redis tạm (vd redis://redis:6379/15)")
def test_redis_counter_store_counts_expires_and_deletes():
    store = RedisCounterStore(os.environ["TEST_REDIS_URL"])
    key = f"test-login-fail:{uuid4()}"
    try:
        assert store.get(key) == (0, 0)
        assert store.increment(key, 30) == 1
        assert store.increment(key, 30) == 2
        count, ttl = store.get(key)
        assert count == 2 and 1 <= ttl <= 30
        store.delete(key)
        assert store.get(key) == (0, 0)
    finally:
        store.delete(key)
