import unittest
from typing import Any

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    import vigia_api.persistence.auth_repository as auth_repository_module
    import vigia_api.services.auth as auth_service_module
    from vigia_api.persistence.auth_repository import SqlAlchemyAuthRepository
    from vigia_api.services.auth import AuthService
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class AuthPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def _service(self) -> Any:
        return AuthService(repository=SqlAlchemyAuthRepository(self.Session))

    def test_login_refresh_logout_and_me_persist(self) -> None:
        service = self._service()
        tokens, session, me = service.login("admin@vigia.local", "change-me-dev", user_agent="pytest", ip_address="127.0.0.1")
        self.assertTrue(tokens.refresh_token)
        self.assertLessEqual(len(session.id), 36)
        self.assertEqual(me.user.email, "admin@vigia.local")

        reloaded = self._service()
        payload = reloaded.me(tokens.access_token)
        self.assertEqual(payload["user"]["email"], "admin@vigia.local")
        self.assertGreaterEqual(len(payload["memberships"]), 1)
        self.assertEqual(payload["active_organization"]["id"], "org-demo")

        refreshed_tokens, refreshed_session, _ = reloaded.refresh(tokens.refresh_token)
        self.assertNotEqual(tokens.refresh_token, refreshed_tokens.refresh_token)
        self.assertIsNotNone(refreshed_session)
        self.assertLessEqual(len(refreshed_session.id), 36)

        after_reload = self._service()
        with self.assertRaises(ValueError):
            after_reload.get_current_user(tokens.access_token)

        after_reload.logout(refreshed_tokens.refresh_token)
        with self.assertRaises(ValueError):
            after_reload.get_current_user(refreshed_tokens.access_token)

    def test_seed_demo_idempotent(self) -> None:
        repo = SqlAlchemyAuthRepository(self.Session)
        repo.seed_demo_user()
        repo.seed_demo_user()
        self.assertIsNotNone(repo.get_user_by_email("admin@vigia.local"))
        self.assertEqual(len(repo.list_memberships("user-dev")), 1)
        self.assertEqual(repo.list_memberships("user-dev")[0].organization.id, "org-demo")

    def test_seed_demo_is_disabled_in_staging_and_production(self) -> None:
        original_auth_env = auth_service_module.settings.app_env
        original_repo_env = auth_repository_module.settings.app_env
        try:
            for env in ("staging", "production"):
                auth_service_module.settings.app_env = env
                auth_repository_module.settings.app_env = env
                repo = SqlAlchemyAuthRepository(self.Session)
                AuthService(repository=repo)
                self.assertIsNone(repo.get_user_by_email("admin@vigia.local"))
                repo.seed_demo_user()
                self.assertIsNone(repo.get_user_by_email("admin@vigia.local"))
        finally:
            auth_service_module.settings.app_env = original_auth_env
            auth_repository_module.settings.app_env = original_repo_env


if __name__ == "__main__":
    unittest.main()
