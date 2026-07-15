import unittest
from typing import cast

from vigia_api import db as db_module
from vigia_api.api.v1 import health as health_module


class HealthTest(unittest.TestCase):
    def test_health_degraded_when_dependency_down(self) -> None:
        original_db = health_module.db_module.check_database_connection
        original_redis = health_module.db_module.check_redis_connection
        original_minio = health_module.db_module.check_minio_connection
        try:
            health_module.db_module.check_database_connection = lambda: db_module.DatabaseCheckResult(ok=True, configured=True, dialect="postgresql", sanitized_url="postgresql://host/db")
            health_module.db_module.check_redis_connection = lambda: db_module.DependencyCheckResult(ok=False, configured=True, sanitized_url="redis://redis:6379/0", error="down")
            health_module.db_module.check_minio_connection = lambda: db_module.DependencyCheckResult(ok=True, configured=True, sanitized_url="http://minio:9000")
            result = cast(dict[str, object], health_module.health())
            self.assertEqual(result["status"], "degraded")
            self.assertIn("dependencies", result)
            dependencies = cast(dict[str, dict[str, object]], result["dependencies"])
            self.assertEqual(dependencies["redis"]["ok"], False)
        finally:
            health_module.db_module.check_database_connection = original_db
            health_module.db_module.check_redis_connection = original_redis
            health_module.db_module.check_minio_connection = original_minio

    def test_health_ok_when_all_dependencies_up(self) -> None:
        original_db = health_module.db_module.check_database_connection
        original_redis = health_module.db_module.check_redis_connection
        original_minio = health_module.db_module.check_minio_connection
        try:
            health_module.db_module.check_database_connection = lambda: db_module.DatabaseCheckResult(ok=True, configured=True, dialect="postgresql", sanitized_url="postgresql://host/db")
            health_module.db_module.check_redis_connection = lambda: db_module.DependencyCheckResult(ok=True, configured=True, sanitized_url="redis://redis:6379/0")
            health_module.db_module.check_minio_connection = lambda: db_module.DependencyCheckResult(ok=True, configured=True, sanitized_url="http://minio:9000")
            result = cast(dict[str, object], health_module.health())
            self.assertEqual(result["status"], "ok")
            self.assertNotIn("secret", str(result))
        finally:
            health_module.db_module.check_database_connection = original_db
            health_module.db_module.check_redis_connection = original_redis
            health_module.db_module.check_minio_connection = original_minio


if __name__ == "__main__":
    unittest.main()
