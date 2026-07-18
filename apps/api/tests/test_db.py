import unittest

from vigia_api.db import check_database_connection, check_minio_connection, is_postgres_url, sanitize_database_url


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
    def test_minio_probe_validates_scheme_and_host_before_urlopen(self) -> None:
        calls = []
        class Dummy:
            s3_endpoint_url = "http://minio:9000"
            minio_endpoint = None
            allow_internal_s3_endpoint = True
        import vigia_api.db as db
        original = db.urlopen
        def fake_urlopen(url, timeout=2):
            calls.append((url, timeout))
            class Resp:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *exc): return False
            return Resp()
        db.urlopen = fake_urlopen
        try:
            ok = check_minio_connection(Dummy())
            self.assertTrue(ok.ok)
            self.assertEqual(len(calls), 1)
            calls.clear()
            class BadScheme(Dummy):
                s3_endpoint_url = "file:///etc/passwd"
            bad = check_minio_connection(BadScheme())
            self.assertFalse(bad.ok)
            self.assertEqual(calls, [])
            class BadCreds(Dummy):
                s3_endpoint_url = "http://user:pass@minio:9000"
            bad2 = check_minio_connection(BadCreds())
            self.assertFalse(bad2.ok)
            self.assertEqual(calls, [])
            class BadHost(Dummy):
                s3_endpoint_url = "http://example.com:9000"
                minio_endpoint = "http://minio:9000"
            bad3 = check_minio_connection(BadHost())
            self.assertFalse(bad3.ok)
            self.assertEqual(calls, [])
        finally:
            db.urlopen = original



if __name__ == "__main__":
    unittest.main()
