import pytest
from fastapi import HTTPException

from app.services import rate_limiter
from app.services.rate_limiter import check_rate_limit


def setup_function():
    with rate_limiter._lock:
        rate_limiter._counters.clear()


def test_allows_requests_under_limit():
    for _ in range(5):
        check_rate_limit("test:key", limit=10)


def test_blocks_when_limit_exceeded():
    for _ in range(5):
        check_rate_limit("test:exceeded", limit=5)
    with pytest.raises(HTTPException) as exc:
        check_rate_limit("test:exceeded", limit=5)
    assert exc.value.status_code == 429


def test_different_keys_are_independent():
    for _ in range(5):
        check_rate_limit("key:a", limit=5)
    # key:b should still be under limit
    check_rate_limit("key:b", limit=5)


def test_window_expiry():
    import time

    for _ in range(3):
        check_rate_limit("test:window", limit=3, window_seconds=0.1)

    with pytest.raises(HTTPException):
        check_rate_limit("test:window", limit=3, window_seconds=0.1)

    time.sleep(0.2)
    # After window expires the counter resets
    check_rate_limit("test:window", limit=3, window_seconds=0.1)
