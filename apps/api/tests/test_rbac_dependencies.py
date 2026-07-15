import unittest

from vigia_api.domain.auth import AuthenticatedUser, MembershipSummary, OrganizationSummary, Permission, PlatformRole, User
from vigia_api.api.v1 import evidence as evidence_api
from vigia_api.security.dependencies import get_current_organization_membership

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]

    from vigia_api.main import app
except Exception:  # pragma: no cover - optional FastAPI test dependency
    TestClient = None  # type: ignore[assignment]
    app = None  # type: ignore[assignment]


class RbacDependenciesTest(unittest.TestCase):
    def setUp(self) -> None:
        org = OrganizationSummary(id="org-1", name="Org 1", slug="org-1")
        self.membership = MembershipSummary(organization=org, role="org_owner", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)
        self.user = AuthenticatedUser(user=User(id="user-1", email="admin@example.com", full_name="Admin", password_hash="x", platform_role=PlatformRole.NONE), memberships=[self.membership])

    def test_membership_dependency_accepts_organization_id(self) -> None:
        membership = get_current_organization_membership(organization_id="org-1", user=self.user)
        self.assertEqual(membership.organization.id, "org-1")

    def test_permission_dependency_denies_foreign_org(self) -> None:
        with self.assertRaises(Exception):
            get_current_organization_membership(organization_id="org-2", user=self.user)

    def test_download_url_uses_current_user_actor(self) -> None:
        class Request:
            method = "POST"
            headers = {"origin": "http://localhost:3000"}
            client = type("Client", (), {"host": "testclient"})()
            url = type("Url", (), {"path": "/api/v1/organizations/org-1/incidents/inc-1/evidence/file-1:download-url"})()

        captured = {}

        original = evidence_api.service.get_download_url

        def fake_get_download_url(organization_id: str, incident_id: str, file_id: str, actor_user_id: str, permission_checked: bool = True):
            captured["actor_user_id"] = actor_user_id
            return {"ok": True}

        evidence_api.service.get_download_url = fake_get_download_url  # type: ignore[assignment]
        try:
            result = evidence_api.download_url("org-1", "inc-1", "file-1", request=Request(), current_user=self.user)
            self.assertEqual(result, {"ok": True})
            self.assertEqual(captured["actor_user_id"], "user-1")
        finally:
            evidence_api.service.get_download_url = original  # type: ignore[assignment]

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_http_protected_route_accepts_organization_id_path_param(self) -> None:
        client = TestClient(app)  # type: ignore[arg-type,operator]
        login = client.post("/api/v1/auth/login", json={"email": "admin@vigia.local", "password": "change-me-dev"}, headers={"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"})
        self.assertEqual(login.status_code, 200)

        response = client.get("/api/v1/organizations/org-dev/incidents")

        self.assertEqual(response.status_code, 200)
        self.assertIn("items", response.json())

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_http_protected_route_denies_unknown_organization(self) -> None:
        client = TestClient(app)  # type: ignore[arg-type,operator]
        login = client.post("/api/v1/auth/login", json={"email": "admin@vigia.local", "password": "change-me-dev"}, headers={"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"})
        self.assertEqual(login.status_code, 200)

        response = client.get("/api/v1/organizations/org-missing/incidents")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
