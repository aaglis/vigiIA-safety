import unittest

from vigia_api.security.csrf import generate_csrf_token, validate_csrf_token
from vigia_api.security.origin import is_allowed_origin
from vigia_api.security.rate_limit import InMemoryRateLimiter


class _LimiterTest(unittest.TestCase):
    def test_csrf_token_generation_and_validation(self) -> None:
        token = generate_csrf_token()
        self.assertTrue(validate_csrf_token(token, token))
        self.assertFalse(validate_csrf_token(token, "other"))
        self.assertFalse(validate_csrf_token(None, token))

    def test_origin_validation_helper(self) -> None:
        self.assertTrue(is_allowed_origin("http://localhost:3000"))
        self.assertFalse(is_allowed_origin("https://evil.example"))

    def test_rate_limiter_fixed_window(self) -> None:
        limiter = InMemoryRateLimiter()
        self.assertTrue(limiter.allow("1:login", 2, 60, now=0))
        self.assertTrue(limiter.allow("1:login", 2, 60, now=1))
        self.assertFalse(limiter.allow("1:login", 2, 60, now=2))
        self.assertTrue(limiter.allow("1:login", 2, 60, now=61))


if __name__ == "__main__":
    unittest.main()
