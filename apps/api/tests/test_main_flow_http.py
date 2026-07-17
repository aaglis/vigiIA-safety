import unittest

from vigia_api.container import build_container
from vigia_api.domain.auth import MembershipSummary, OrganizationSummary, Permission
from vigia_api.domain.edge_workers import EdgeWorker
from vigia_api.services.security import hash_token
from vigia_api.settings import settings
from vigia_api.security.rate_limit import rate_limiter

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]

    from vigia_api.main import create_app
except Exception:  # pragma: no cover - optional FastAPI test dependency
    TestClient = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


ORIGIN_HEADERS = {"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"}


class MainFlowHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        rate_limiter._windows.clear()
        if TestClient is None:
            self.skipTest("fastapi test client unavailable")
        assert create_app is not None

        self.container = build_container(repository_backend="memory", seed_dev=False)
        self._seed_org_demo_membership(self.container.auth_service)
        self._seed_edge_worker_demo()
        self.client = TestClient(create_app(container=self.container))  # type: ignore[arg-type,operator]

    def _seed_org_demo_membership(self, auth_service) -> None:
        auth_service.repository.seed_demo_user()
        user = auth_service.repository.get_user_by_email("admin@vigia.local")
        self.assertIsNotNone(user)
        org = OrganizationSummary(id="org-demo", name="VigIA Local", slug="vigia-local")
        membership = MembershipSummary(
            organization=org,
            role="org_owner",
            permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG],
            active=True,
        )
        memberships = [item for item in auth_service.repository.memberships.get(user.id, []) if item.organization.id != "org-demo"]
        auth_service.repository.memberships[user.id] = [membership, *memberships]

    def _seed_edge_worker_demo(self) -> None:
        worker = EdgeWorker(
            id="edge-worker-demo",
            organization_id="org-demo",
            site_id="site-demo",
            name="Edge Worker Demo",
            client_id=settings.edge_worker_client_id,
            api_key_hash=hash_token(settings.edge_worker_api_key),
            allowed_camera_ids=["camera-demo-01"],
        )
        self.container.edge_worker_service.repository.save(worker)
        self.container.edge_worker_service.camera_catalog[(worker.organization_id, worker.site_id)] = set(worker.allowed_camera_ids)

    def test_http_main_flow_login_edge_incident_audit_and_evidence(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@vigia.local", "password": "change-me-dev"},
            headers=ORIGIN_HEADERS,
        )
        self.assertEqual(login.status_code, 200)
        self.assertNotIn("refresh_token", login.json()["tokens"])
        self.assertNotIn("password_hash", login.json()["me"]["user"])
        self.assertEqual(login.json()["me"]["active_organization"]["id"], "org-demo")

        me = self.client.get("/api/v1/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "admin@vigia.local")
        csrf_token = self.client.cookies.get(settings.csrf_cookie_name)
        self.assertTrue(csrf_token)
        browser_mutation_headers = {**ORIGIN_HEADERS, settings.csrf_header_name: str(csrf_token)}

        edge_headers = {"X-Edge-Client-Id": settings.edge_worker_client_id, "X-Edge-Api-Key": settings.edge_worker_api_key}
        config = self.client.get("/api/v1/edge-workers/me/config", headers=edge_headers)
        self.assertEqual(config.status_code, 200)
        self.assertEqual(config.json()["worker"]["organization_id"], "org-demo")
        self.assertNotIn("api_key_hash", config.json()["worker"])

        heartbeat = self.client.post("/api/v1/edge-workers/me/heartbeat", headers=edge_headers)
        self.assertEqual(heartbeat.status_code, 200)

        detection = self.client.post(
            "/api/v1/edge-workers/me/detections",
            headers=edge_headers,
            json={
                "organization_id": "org-demo",
                "site_id": "site-demo",
                "camera_id": "camera-demo-01",
                "zone_id": "zone-demo-01",
                "event_type": "mock_detection",
                "severity": "high",
                "confidence": 0.92,
                "model_version": "mock-vision-0",
                "summary": "Pessoa em zona restrita",
            },
        )
        self.assertEqual(detection.status_code, 201)
        incident_id = detection.json()["incident"]["id"]

        incident_list = self.client.get("/api/v1/organizations/org-demo/incidents")
        self.assertEqual(incident_list.status_code, 200)
        self.assertEqual([item["id"] for item in incident_list.json()["items"]], [incident_id])

        filtered_by_status = self.client.get("/api/v1/organizations/org-demo/incidents", params={"status": "open"})
        self.assertEqual(filtered_by_status.status_code, 200)
        self.assertEqual([item["id"] for item in filtered_by_status.json()["items"]], [incident_id])

        filtered_by_severity = self.client.get("/api/v1/organizations/org-demo/incidents", params={"severity": "high"})
        self.assertEqual(filtered_by_severity.status_code, 200)
        self.assertEqual([item["id"] for item in filtered_by_severity.json()["items"]], [incident_id])

        filtered_by_site_camera_zone = self.client.get(
            "/api/v1/organizations/org-demo/incidents",
            params={"site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01"},
        )
        self.assertEqual(filtered_by_site_camera_zone.status_code, 200)
        self.assertEqual([item["id"] for item in filtered_by_site_camera_zone.json()["items"]], [incident_id])

        created_at = incident_list.json()["items"][0]["created_at"]
        created_window = self.client.get(
            "/api/v1/organizations/org-demo/incidents",
            params={"created_from": created_at, "created_to": created_at},
        )
        self.assertEqual(created_window.status_code, 200)
        self.assertEqual([item["id"] for item in created_window.json()["items"]], [incident_id])

        paginated = self.client.get("/api/v1/organizations/org-demo/incidents", params={"limit": 1, "offset": 0, "severity": "high"})
        self.assertEqual(paginated.status_code, 200)
        self.assertEqual(paginated.json()["page_info"], {"limit": 1, "offset": 0, "total": 1, "has_next": False})

        incident_detail = self.client.get(f"/api/v1/organizations/org-demo/incidents/{incident_id}")
        self.assertEqual(incident_detail.status_code, 200)
        self.assertEqual(incident_detail.json()["status"], "open")

        missing_csrf = self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident_id}:acknowledge", headers=ORIGIN_HEADERS)
        self.assertEqual(missing_csrf.status_code, 403)

        bad_origin = self.client.post(
            f"/api/v1/organizations/org-demo/incidents/{incident_id}:acknowledge",
            headers={"Origin": "https://evil.example", settings.csrf_header_name: str(csrf_token)},
        )
        self.assertEqual(bad_origin.status_code, 403)

        acknowledged = self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident_id}:acknowledge", headers=browser_mutation_headers)
        self.assertEqual(acknowledged.status_code, 200)
        self.assertEqual(acknowledged.json()["status"], "acknowledged")

        resolved = self.client.post(
            f"/api/v1/organizations/org-demo/incidents/{incident_id}:resolve",
            headers=browser_mutation_headers,
            json={"reason": "Operador confirmou EPI e encerrou o risco."},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["status"], "resolved")

        audit = self.client.get(f"/api/v1/organizations/org-demo/incidents/{incident_id}/audit-log")
        self.assertEqual(audit.status_code, 200)
        self.assertEqual([item["to_status"] for item in audit.json()["items"]], ["open", "acknowledged", "resolved"])

        file_id = "snapshot-e2e-01"
        upload = self.client.post(
            f"/api/v1/organizations/org-demo/incidents/{incident_id}/evidence/{file_id}:upload-url",
            headers=browser_mutation_headers,
            json={"media_type": "image/jpeg", "size": 1024, "uploaded_by": "user-dev", "source": "user"},
        )
        self.assertEqual(upload.status_code, 200)
        self.assertIn("upload_url", upload.json())

        download = self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident_id}/evidence/{file_id}:download-url", headers=browser_mutation_headers)
        self.assertEqual(download.status_code, 200)
        self.assertIn("download_url", download.json())

        foreign_org = self.client.get("/api/v1/organizations/org-other/incidents")
        self.assertEqual(foreign_org.status_code, 403)

        foreign_evidence = self.client.post(f"/api/v1/organizations/org-other/incidents/{incident_id}/evidence/{file_id}:download-url", headers=browser_mutation_headers)
        self.assertEqual(foreign_evidence.status_code, 403)

    def test_refresh_requires_csrf_cookie_header_match(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@vigia.local", "password": "change-me-dev"},
            headers=ORIGIN_HEADERS,
        )
        self.assertEqual(login.status_code, 200)

        without_header = self.client.post("/api/v1/auth/refresh", headers=ORIGIN_HEADERS)
        self.assertEqual(without_header.status_code, 403)

        csrf_token = self.client.cookies.get(settings.csrf_cookie_name)
        self.assertTrue(csrf_token)
        with_header = self.client.post(
            "/api/v1/auth/refresh",
            headers={**ORIGIN_HEADERS, settings.csrf_header_name: str(csrf_token)},
        )
        self.assertEqual(with_header.status_code, 200)
        self.assertIn("tokens", with_header.json())

        invalid_origin = self.client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://evil.example", settings.csrf_header_name: str(self.client.cookies.get(settings.csrf_cookie_name))},
        )
        self.assertEqual(invalid_origin.status_code, 403)

        logout = self.client.post(
            "/api/v1/auth/logout",
            headers={**ORIGIN_HEADERS, settings.csrf_header_name: str(self.client.cookies.get(settings.csrf_cookie_name))},
        )
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(logout.json()["status"], "ok")

        after_logout = self.client.get("/api/v1/auth/me")
        self.assertEqual(after_logout.status_code, 401)


if __name__ == "__main__":
    unittest.main()
