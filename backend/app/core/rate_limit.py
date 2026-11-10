"""Giới hạn số lần đăng nhập sai (S3-04).

Đếm lần sai theo (IP, username) và theo IP; vượt ngưỡng trong một cửa sổ thời gian thì từ chối đăng nhập
bằng 429 cho tới khi cửa sổ hết hạn. Đăng nhập đúng xóa bộ đếm (IP, username).

- Bộ đếm nằm trong Redis (đã dùng cho RQ) nên dùng chung giữa các process API; không thêm thư viện.
- Redis lỗi thì cho qua (fail-open) và ghi log: không để Redis chết khóa toàn bộ người dùng.
- IP lấy từ `request.client.host`. Sau reverse proxy cần cấu hình proxy headers, nếu không mọi người dùng
  chung một IP của proxy.
"""
import logging
import time
from typing import Callable, Protocol

from redis import Redis

from app.core.limits import LOGIN_IP_MAX_FAILURES, LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS
from app.core.queue import REDIS_URL

logger = logging.getLogger(__name__)


class CounterStore(Protocol):
    def increment(self, key: str, window_seconds: int) -> int:
        """Tăng bộ đếm; lần tăng đầu tiên đặt thời hạn `window_seconds`. Trả về giá trị mới."""

    def get(self, key: str) -> tuple[int, int]:
        """Trả về (giá trị, số giây còn lại); (0, 0) nếu chưa có hoặc đã hết hạn."""

    def delete(self, key: str) -> None: ...


class RedisCounterStore:
    def __init__(self, url: str):
        # Timeout ngắn: Redis không phản hồi không được làm treo request đăng nhập.
        self._redis = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)

    def increment(self, key: str, window_seconds: int) -> int:
        pipeline = self._redis.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, window_seconds, nx=True)
        count, _ = pipeline.execute()
        return int(count)

    def get(self, key: str) -> tuple[int, int]:
        pipeline = self._redis.pipeline()
        pipeline.get(key)
        pipeline.ttl(key)
        value, ttl = pipeline.execute()
        if value is None:
            return 0, 0
        return int(value), max(int(ttl), 0)

    def delete(self, key: str) -> None:
        self._redis.delete(key)


class MemoryCounterStore:
    """Cài đặt trong bộ nhớ, dùng cho test (đồng hồ thay được)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._items: dict[str, tuple[int, float]] = {}

    def _live(self, key: str) -> tuple[int, float] | None:
        item = self._items.get(key)
        if item is None or item[1] <= self._clock():
            self._items.pop(key, None)
            return None
        return item

    def increment(self, key: str, window_seconds: int) -> int:
        item = self._live(key)
        count, expires_at = item if item else (0, self._clock() + window_seconds)
        self._items[key] = (count + 1, expires_at)
        return count + 1

    def get(self, key: str) -> tuple[int, int]:
        item = self._live(key)
        if item is None:
            return 0, 0
        return item[0], max(int(item[1] - self._clock() + 0.999), 0)

    def delete(self, key: str) -> None:
        self._items.pop(key, None)


class LoginRateLimiter:
    def __init__(
        self,
        store: CounterStore,
        max_failures: int = LOGIN_MAX_FAILURES,
        ip_max_failures: int = LOGIN_IP_MAX_FAILURES,
        window_seconds: int = LOGIN_WINDOW_SECONDS,
    ):
        self._store = store
        self._max_failures = max_failures
        self._ip_max_failures = ip_max_failures
        self._window_seconds = window_seconds

    @staticmethod
    def _keys(ip: str, username: str) -> tuple[str, str]:
        return f"login-fail:ip:{ip}", f"login-fail:ip-user:{ip}:{username}"

    def retry_after(self, ip: str, username: str) -> int:
        """Số giây phải chờ; 0 nghĩa là được phép thử."""
        ip_key, pair_key = self._keys(ip, username)
        try:
            waits = []
            for key, limit in ((ip_key, self._ip_max_failures), (pair_key, self._max_failures)):
                count, ttl = self._store.get(key)
                if count >= limit:
                    waits.append(max(ttl, 1))
            return max(waits, default=0)
        except Exception:
            logger.warning("Login rate limiter unavailable; allowing the attempt", exc_info=True)
            return 0

    def record_failure(self, ip: str, username: str) -> None:
        try:
            for key in self._keys(ip, username):
                self._store.increment(key, self._window_seconds)
        except Exception:
            logger.warning("Login rate limiter unavailable; failure not counted", exc_info=True)

    def reset(self, ip: str, username: str) -> None:
        try:
            self._store.delete(self._keys(ip, username)[1])
        except Exception:
            logger.warning("Login rate limiter unavailable; counter not reset", exc_info=True)


_limiter: LoginRateLimiter | None = None


def get_login_limiter() -> LoginRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = LoginRateLimiter(RedisCounterStore(REDIS_URL))
    return _limiter
