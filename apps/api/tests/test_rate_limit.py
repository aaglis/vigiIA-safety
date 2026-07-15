import unittest
from types import SimpleNamespace

from vigia_api.security import rate_limit as rl


class DummyClient:
    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host


class DummyRequest:
    def __init__(self, path: str = "/auth/login", host: str = "127.0.0.1") -> None:
        self.client = DummyClient(host)
        self.url = SimpleNamespace(path=path)


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    class Pipeline:
        def __init__(self, parent: "FakeRedis") -> None:
            self.parent = parent
            self._ops: list[tuple[str, tuple]] = []

        def incr(self, key: str):
            self._ops.append(("incr", (key,)))
            return self

        def expire(self, key: str, seconds: int, nx: bool = False):
            self._ops.append(("expire", (key, seconds, nx)))
            return self

        def execute(self):
            result = []
            for op, args in self._ops:
                if op == "incr":
                    key = args[0]
                    self.parent.store[key] = self.parent.store.get(key, 0) + 1
                    result.append(self.parent.store[key])
                elif op == "expire":
                    key, seconds, nx = args
                    if nx and key in self.parent.expiries:
                        result.append(False)
                    else:
                        self.parent.expiries[key] = seconds
                        result.append(True)
            return result

    def pipeline(self):
        return FakeRedis.Pipeline(self)


class RateLimitTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_backend = rl.settings.rate_limit_backend
        self._orig_env = rl.settings.app_env
        self._orig_redis = rl.redis

    def tearDown(self) -> None:
        rl.settings.rate_limit_backend = self._orig_backend
        rl.settings.app_env = self._orig_env
        rl.redis = self._orig_redis

    def test_memory_backend_limits_by_ip_and_resets_window(self) -> None:
        limiter = rl.InMemoryRateLimiter()
        self.assertTrue(limiter.allow("k", 1, 60, now=0))
        self.assertFalse(limiter.allow("k", 1, 60, now=1))
        self.assertTrue(limiter.allow("k", 1, 60, now=61))

    def test_redis_backend_uses_hashed_keys_and_ttl(self) -> None:
        fake_redis = FakeRedis()
        rl.redis = SimpleNamespace(Redis=SimpleNamespace(from_url=lambda url, decode_responses=True: fake_redis))
        rl.settings.rate_limit_backend = "redis"
        limiter = rl.RedisRateLimiter("redis://localhost:6379/0")
        self.assertTrue(limiter.allow(rl._scope_key("auth.login", ip="127.0.0.1", email="test@example.com"), 2, 60))
        self.assertEqual(next(iter(fake_redis.expiries.values())), 60)
        self.assertTrue(all("test@example.com" not in key for key in fake_redis.store.keys()))

    def test_rate_limit_raises_429_and_masks_identifiers(self) -> None:
        rl.settings.rate_limit_backend = "memory"
        req = DummyRequest(path="/auth/login")
        rl.rate_limiter = rl.InMemoryRateLimiter()
        rl.rate_limit(req, "auth.login", 1, 60, email="hidden@example.com")
        with self.assertRaises(rl.HTTPException) as ctx:
            rl.rate_limit(req, "auth.login", 1, 60, email="hidden@example.com")
        self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
