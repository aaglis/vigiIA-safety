import unittest

from sqlalchemy.exc import IntegrityError

from vigia_api.persistence.repositories import SqlAlchemyIncidentRepository


class IncidentIdempotencyConstraintTest(unittest.TestCase):
    def _repo(self) -> SqlAlchemyIncidentRepository:
        return SqlAlchemyIncidentRepository(lambda: None)

    def test_sqlite_unique_detection_event_violation_is_idempotent(self) -> None:
        error = IntegrityError(
            "insert",
            {},
            Exception("UNIQUE constraint failed: incidents.organization_id, incidents.detection_event_id"),
        )

        self.assertTrue(self._repo()._is_detection_event_unique_violation(error))

    def test_unrelated_integrity_error_is_not_idempotent(self) -> None:
        error = IntegrityError("insert", {}, Exception("NOT NULL constraint failed: incidents.summary"))

        self.assertFalse(self._repo()._is_detection_event_unique_violation(error))


if __name__ == "__main__":
    unittest.main()
