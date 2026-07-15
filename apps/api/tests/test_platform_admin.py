import unittest
from typing import cast

from vigia_api.domain.auth import PlatformRole, User
from vigia_api.services.auth import InMemoryAuthRepository
from vigia_api.services.platform_admin import PlatformAdminService
from vigia_api.services.security import hash_password
from vigia_api.api.v1 import platform as platform_api


class PlatformAdminTest(unittest.TestCase):
    def setUp(self) -> None:
        self.auth_repo = InMemoryAuthRepository()
        admin = User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER)
        self.auth_repo.add_user(admin)
        self.service = PlatformAdminService(self.auth_repo)

    def test_create_suspend_reactivate_and_audit(self) -> None:
        org = self.service.create_organization(name="Acme", legal_name="Acme LTDA", tax_id="12.345.678/0001-90", created_by_user_id="platform-admin", leader_email="leader@acme.local", plan="pro")
        items = self.service.list_organizations()
        self.assertEqual(len(items), 1)
        health = cast(dict[str, object], items[0]["health"])
        self.assertEqual(health["status"], "active")
        self.assertEqual(len(self.service.audit_logs), 2)
        suspended = self.service.suspend_organization(org.id, "platform-admin")
        self.assertEqual(suspended.status.value, "suspended")
        reactivated = self.service.reactivate_organization(org.id, "platform-admin")
        self.assertEqual(reactivated.status.value, "active")
        self.assertEqual(len(self.service.audit_logs), 4)

    def test_requires_platform_role(self) -> None:
        user = User(id="normal", email="user@vigia.local", full_name="User", password_hash=hash_password("pw"))
        self.auth_repo.add_user(user)
        with self.assertRaises(PermissionError):
            self.service.create_organization(name="A", legal_name="A", tax_id="1", created_by_user_id="normal")

    def test_org_admin_cannot_create_global_organization(self) -> None:
        org_admin = User(id="org-admin", email="admin@org.local", full_name="Org Admin", password_hash=hash_password("pw"))
        self.auth_repo.add_user(org_admin)
        with self.assertRaises(PermissionError):
            self.service.create_organization(name="A", legal_name="A", tax_id="1", created_by_user_id="org-admin")

    def test_route_ignores_spoofed_actor_and_uses_current_user(self) -> None:
        class CurrentUser:
            def __init__(self, user_id: str) -> None:
                self.user = type("U", (), {"id": user_id})()

        class Request:
            headers = {"origin": "http://localhost:3000", "referer": "http://localhost:3000/"}
            method = "POST"
            cookies = {}
            client = None
            url = type("U", (), {"path": "/api/v1/platform/organizations"})()
            app = type("App", (), {"state": type("State", (), {})()})()

        platform_api.auth_service.repository.add_user(User(id="platform-admin", email="admin2@vigia.local", full_name="Owner2", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER))
        payload = platform_api.OrganizationIn(name="Spoof Test", legal_name="Spoof Test LTDA", tax_id="12", leader_email="lead@x.local", created_by_user_id="spoofed")
        result = platform_api.create_organization(payload, request=Request(), current_user=CurrentUser("platform-admin"))
        self.assertEqual(result["organization"]["created_by_user_id"], "platform-admin")


if __name__ == "__main__":
    unittest.main()
