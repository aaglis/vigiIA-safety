import unittest

from vigia_api.db import check_database_connection, is_postgres_url, sanitize_database_url


class DatabaseTest(unittest.TestCase):
    def test_sanitization_removes_password(self) -> None:
        url = "postgresql+psycopg://user:secret@localhost:5432/vigia"
        sanitized = sanitize_database_url(url)
        self.assertNotIn("secret", sanitized)
        self.assertIn("***", sanitized)

    def test_postgres_url_detection(self) -> None:
        self.assertTrue(is_postgres_url("postgresql+psycopg://user:pass@localhost/db"))
        self.assertTrue(is_postgres_url("postgresql://localhost/db"))
        self.assertFalse(is_postgres_url("sqlite:///tmp.db"))

    def test_missing_or_invalid_url_is_handled(self) -> None:
        self.assertEqual(sanitize_database_url(None), "<not-configured>")
        self.assertEqual(sanitize_database_url("not-a-url"), "<invalid-database-url>")

    def test_health_check_uses_fake_probe(self) -> None:
        class DummySettings:
            database_url = "postgresql+psycopg://user:secret@localhost:5432/vigia"

            @staticmethod
            def database_probe(timeout_seconds: int = 2) -> bool:
                return True

        result = check_database_connection(DummySettings(), timeout_seconds=1)
        self.assertTrue(result.ok)
        self.assertTrue(result.configured)
        self.assertNotIn("secret", result.sanitized_url)


if __name__ == "__main__":
    unittest.main()
