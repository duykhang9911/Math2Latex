import os

import pytest

os.environ.setdefault("DB_URL", "sqlite://")
os.environ.setdefault("AUTH_SECRET", "test-auth-secret-that-is-long-enough-123456")

from app.core import rate_limit  # noqa: E402  (sau khi đặt biến môi trường)


@pytest.fixture(autouse=True)
def _isolated_login_limiter(monkeypatch):
    """Test không được chạm Redis thật: mỗi test dùng bộ đếm đăng nhập trong bộ nhớ."""
    limiter = rate_limit.LoginRateLimiter(
        rate_limit.MemoryCounterStore(), max_failures=3, ip_max_failures=10, window_seconds=60
    )
    monkeypatch.setattr(rate_limit, "_limiter", limiter)
    return limiter
