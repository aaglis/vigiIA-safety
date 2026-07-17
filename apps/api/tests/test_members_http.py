import unittest

from vigia_api.container import build_container
from vigia_api.domain.auth import MembershipSummary, OrganizationSummary, Permission, User
from vigia_api.security.rate_limit import rate_limiter
from vigia_api.settings import settings

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]

    from vigia_api.main import create_app
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


ORIGIN_HEADERS = {"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"}


class MembersHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        # O limitador é singleton de módulo: sem limpar, os logins dos testes anteriores
        # (mesmo IP, mesmo admin@vigia.local) gastam as 5 tentativas/min e o login aqui
        # volta 429. Passa isolado, quebra na suíte.
        rate_limiter._windows.clear()
        if TestClient is None:
            self.skipTest("fastapi test client unavailable")
        assert create_app is not None
        self.container = build_container(repository_backend="memory", seed_dev=False)
        self.container.auth_service.repository.seed_demo_user()
        user = self.container.auth_service.repository.get_user_by_email("admin@vigia.local")
        assert user is not None
        self.user = user
        assert self.user is not None
        self.org = OrganizationSummary(id="org-demo", name="VigIA Local", slug="vigia-local")
        self.container.auth_service.repository.memberships[self.user.id] = [MembershipSummary(organization=self.org, role="org_owner", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)]
        self.container.auth_service.repository.users["member-1"] = User(id="member-1", email="member@vigia.local", full_name="Member One", password_hash=self.user.password_hash)
        self.container.auth_service.repository.memberships["member-1"] = [MembershipSummary(organization=self.org, role="manager", permissions=[Permission.VIEW_DASHBOARD], active=True)]
        self.client = TestClient(create_app(container=self.container))  # type: ignore[arg-type,operator]
        login = self.client.post("/api/v1/auth/login", json={"email": "admin@vigia.local", "password": "change-me-dev"}, headers=ORIGIN_HEADERS)
        self.assertEqual(login.status_code, 200)
        self.csrf = self.client.cookies.get(settings.csrf_cookie_name)
        self.assertTrue(self.csrf)
        self.headers = {**ORIGIN_HEADERS, settings.csrf_header_name: str(self.csrf)}

    def test_list_patch_delete_members(self) -> None:
        resp = self.client.get("/api/v1/organizations/org-demo/members")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["items"][0]["user"]["email"], "admin@vigia.local")

        patched = self.client.patch("/api/v1/organizations/org-demo/members/member-1", headers=self.headers, json={"active": False})
        self.assertEqual(patched.status_code, 200)
        self.assertFalse(patched.json()["member"]["active"])

        deleted = self.client.delete("/api/v1/organizations/org-demo/members/member-1", headers=self.headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(deleted.json()["member"]["active"])

    def test_missing_permission_denies_list(self) -> None:
        assert self.user is not None
        self.container.auth_service.repository.memberships[self.user.id][0] = MembershipSummary(organization=self.org, role="manager", permissions=[Permission.VIEW_DASHBOARD], active=True)
        resp = self.client.get("/api/v1/organizations/org-demo/members")
        self.assertEqual(resp.status_code, 403)

    def test_csrf_required_for_patch_and_delete(self) -> None:
        no_csrf = self.client.patch("/api/v1/organizations/org-demo/members/member-1", headers=ORIGIN_HEADERS, json={"active": False})
        self.assertEqual(no_csrf.status_code, 403)
        bad_csrf = self.client.delete("/api/v1/organizations/org-demo/members/member-1", headers={**ORIGIN_HEADERS, settings.csrf_header_name: "bad"})
        self.assertEqual(bad_csrf.status_code, 403)

    def test_foreign_org_denied(self) -> None:
        resp = self.client.get("/api/v1/organizations/org-other/members")
        self.assertEqual(resp.status_code, 403)

    def test_last_owner_guard(self) -> None:
        resp = self.client.patch(f"/api/v1/organizations/org-demo/members/{self.user.id}", headers=self.headers, json={"role": "org_admin"})
        self.assertEqual(resp.status_code, 409)


if __name__ == "__main__":
    unittest.main()
