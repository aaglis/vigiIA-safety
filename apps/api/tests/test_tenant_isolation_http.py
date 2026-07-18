import unittest
from typing import cast

from vigia_api.container import build_container
from vigia_api.domain.auth import MembershipSummary, OrganizationSummary, Permission, PlatformRole, User
from vigia_api.domain.edge_workers import EdgeWorker
from vigia_api.domain.evidence import EvidenceKind, EvidenceSource
from vigia_api.domain.incidents import parse_detection_event
from vigia_api.domain.operations import ZoneType
from vigia_api.services.security import hash_password, hash_token
from vigia_api.security.rate_limit import rate_limiter
from vigia_api.settings import settings

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]
    from vigia_api.main import create_app
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


ORIGIN_HEADERS = {"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"}


class TenantIsolationHttpTest(unittest.TestCase):
    def setUp(self) -> None:
        if TestClient is None or create_app is None:
            self.skipTest("fastapi test client unavailable")
        # `settings` é singleton de módulo: sem restaurar, o resto da suíte herda limite
        # 1000 e passa a rodar sem rate limit — um teste de "bloqueia após N tentativas"
        # ficaria verde com o limitador desligado.
        afrouxados = {"login_rate_limit_attempts": 1000, "auth_rate_limit_attempts": 1000, "sensitive_rate_limit_attempts": 1000}
        for nome, valor in afrouxados.items():
            self.addCleanup(setattr, settings, nome, getattr(settings, nome))
            setattr(settings, nome, valor)
        rate_limiter._windows.clear()
        self.container = build_container(repository_backend="memory", seed_dev=False)
        self.container.auth_service.repository.seed_demo_user()
        user = self.container.auth_service.repository.get_user_by_email("admin@vigia.local")
        assert user is not None
        org = OrganizationSummary(id="org-demo", name="VigIA Demo", slug="vigia-demo")
        self.container.auth_service.repository.memberships[user.id] = [MembershipSummary(organization=org, role="org_owner", permissions=[Permission.VIEW_DASHBOARD, Permission.MANAGE_USERS, Permission.MANAGE_ORG], active=True)]
        self.container.auth_service.repository.add_user(User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER))
        self.worker = EdgeWorker(id="edge-worker-demo", organization_id="org-demo", site_id="site-demo", name="Edge Worker Demo", client_id=settings.edge_worker_client_id, api_key_hash=hash_token(settings.edge_worker_api_key), allowed_camera_ids=["camera-demo-01"])
        self.container.edge_worker_service.repository.save(self.worker)
        self.container.edge_worker_service.camera_catalog[("org-demo", "site-demo")] = {"camera-demo-01"}
        ops = self.container.operations_repository
        site = ops.create_site("org-demo", "HQ", "Main street", site_id="site-demo")
        camera = ops.create_camera("org-demo", site.id, "Gate", "stream-1", camera_id="camera-demo-01")
        zone = ops.create_zone("org-demo", site.id, camera.id, ZoneType.ACCESS, {"points": [[0, 0], [1, 1]]}, zone_id="zone-demo-01")
        rule = ops.create_safety_rule("org-demo", "Helmet required", site_id=site.id, zone_id=zone.id)
        ops.create_required_ppe("org-demo", rule.id, "helmet", site_id=site.id, zone_id=zone.id)
        other_site = ops.create_site("org-other", "Other HQ")
        other_camera = ops.create_camera("org-other", other_site.id, "Other Cam", "stream-other")
        ops.create_zone("org-other", other_site.id, other_camera.id, ZoneType.ACCESS, {"points": []}, zone_id="zone-other-01")
        self.client = TestClient(create_app(container=self.container))
        login = self.client.post("/api/v1/auth/login", json={"email": "admin@vigia.local", "password": "change-me-dev"}, headers=ORIGIN_HEADERS)
        self.assertEqual(login.status_code, 200)
        self.csrf = str(self.client.cookies.get(settings.csrf_cookie_name))

    def test_cross_tenant_incidents_evidence_and_platform_are_blocked(self) -> None:
        self.assertEqual(self.client.get("/api/v1/organizations/org-other/incidents").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/organizations/org-other/evidence").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/organizations/org-other/evidence/audit-logs").status_code, 403)
        incident_repo = cast(object, self.container.incident_repository)
        incident = getattr(incident_repo, "create_from_detection")(parse_detection_event({"organization_id": "org-demo", "site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "high", "event_id": "evt-demo-1"}))
        getattr(incident_repo, "create_from_detection")(parse_detection_event({"organization_id": "org-demo", "site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "low", "event_id": "evt-demo-2"}))
        getattr(incident_repo, "create_from_detection")(parse_detection_event({"organization_id": "org-demo", "site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "high", "event_id": "evt-demo-3"}))
        self.container.evidence_service.register_evidence("org-demo", incident.id, "file-1", "image/jpeg", 1, "user-dev", EvidenceSource.USER, EvidenceKind.SNAPSHOT)
        self.assertEqual(self.client.get(f"/api/v1/organizations/org-other/incidents/{incident.id}").status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/organizations/org-other/incidents/{incident.id}/evidence/file-1:download-url", headers={**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}).status_code, 403)
        filtered = self.client.get("/api/v1/organizations/org-demo/incidents", params={"status": "open", "severity": "high", "site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "limit": 2, "offset": 0})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["page_info"], {"limit": 2, "offset": 0, "total": 2, "has_next": False})
        self.assertTrue(all(item["site_id"] == "site-demo" for item in filtered.json()["items"]))
        foreign_filter = self.client.get("/api/v1/organizations/org-demo/incidents", params={"site_id": "site-other", "camera_id": "camera-other", "zone_id": "zone-other-01"})
        self.assertEqual(foreign_filter.status_code, 200)
        self.assertEqual(foreign_filter.json()["items"], [])
        self.assertEqual(self.client.get("/api/v1/platform/organizations").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/organizations/org-other/invites", json={"email": "x@x.local", "role": "org_admin"}, headers={**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}).status_code, 403)

    def test_edge_worker_scope_mismatch_is_rejected(self) -> None:
        headers = {"X-Edge-Client-Id": settings.edge_worker_client_id, "X-Edge-Api-Key": settings.edge_worker_api_key}
        self.assertEqual(self.client.post("/api/v1/edge-workers/me/detections", headers=headers, json={"organization_id": "org-other", "site_id": "site-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "high"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/edge-workers/me/detections", headers=headers, json={"organization_id": "org-demo", "site_id": "site-other", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "high"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/edge-workers/me/detections", headers=headers, json={"organization_id": "org-demo", "site_id": "site-demo", "camera_id": "camera-other", "zone_id": "zone-demo-01", "severity": "high"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/edge-workers/me/evidence-upload?file_id=file-1", headers=headers).status_code, 200)

    def test_csrf_and_origin_required_on_mutations(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        incident_repo = cast(object, self.container.incident_repository)
        incident = getattr(incident_repo, "create_from_detection")(parse_detection_event({"organization_id": "org-demo", "camera_id": "camera-demo-01", "zone_id": "zone-demo-01", "severity": "high"}))
        self.assertEqual(self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident.id}:acknowledge", headers=ORIGIN_HEADERS).status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident.id}:resolve", headers={"Origin": "https://evil.example", settings.csrf_header_name: self.csrf}, json={"reason": "fixed"}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/organizations/org-demo/incidents/{incident.id}:acknowledge", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/organizations/org-demo/invites", json={"email": "new@vigia.local", "role": "org_admin"}, headers=ORIGIN_HEADERS).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/platform/organizations", json={"name": "X", "legal_name": "X", "tax_id": "1", "created_by_user_id": "spoof"}, headers=ORIGIN_HEADERS).status_code, 403)

    def test_mutations_accept_csrf_and_good_origin(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        invite = self.client.post("/api/v1/organizations/org-demo/invites", json={"email": "new@vigia.local", "role": "org_admin"}, headers=headers)
        self.assertEqual(invite.status_code, 200)
        platform = self.client.post("/api/v1/platform/organizations", json={"name": "New Org", "legal_name": "New Org LTDA", "tax_id": "12", "created_by_user_id": "spoof"}, headers=headers)
        self.assertIn(platform.status_code, {200, 403})

    def test_operations_catalog_blocks_cross_tenant_relations(self) -> None:
        repo = self.container.operations_repository
        site = repo.create_site("org-demo", "HQ")
        other_site = repo.create_site("org-other", "Other")
        other_camera = repo.create_camera("org-other", other_site.id, "Other camera", "rtsp://example")
        with self.assertRaises(KeyError):
            repo.create_camera("org-demo", other_site.id, "Bad camera", "rtsp://bad")
        with self.assertRaises(KeyError):
            repo.create_zone("org-demo", site.id, other_camera.id, ZoneType.ACCESS, {"points": []})
        with self.assertRaises(KeyError):
            repo.ensure_camera_scope("org-demo", other_site.id, other_camera.id)

    def test_operations_catalog_is_tenant_scoped_and_renderable(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        response = self.client.get("/api/v1/organizations/org-demo/operations/catalog", headers=headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["organization_id"], "org-demo")
        self.assertEqual(len(payload["sites"]), 1)
        self.assertEqual(payload["sites"][0]["id"], "site-demo")
        self.assertEqual(payload["sites"][0]["cameras"][0]["id"], "camera-demo-01")
        self.assertEqual(payload["sites"][0]["zones"][0]["id"], "zone-demo-01")
        self.assertEqual(payload["sites"][0]["safety_rules"][0]["name"], "Helmet required")
        self.assertEqual(payload["sites"][0]["required_ppe"][0]["item"], "helmet")
        self.assertEqual(self.client.get("/api/v1/organizations/org-other/operations/catalog").status_code, 403)

    def test_operations_dedicated_lists_expose_ids(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        sites = self.client.get("/api/v1/organizations/org-demo/operations/sites", headers=headers).json()["items"]
        cameras = self.client.get("/api/v1/organizations/org-demo/operations/cameras", headers=headers).json()["items"]
        zones = self.client.get("/api/v1/organizations/org-demo/operations/zones", headers=headers).json()["items"]
        self.assertEqual(sites[0]["id"], "site-demo")
        self.assertEqual(cameras[0]["site_id"], "site-demo")
        self.assertEqual(zones[0]["camera_id"], "camera-demo-01")
        for path in ("sites", "cameras", "zones", "safety-rules", "required-ppe"):
            self.assertEqual(self.client.get(f"/api/v1/organizations/org-other/operations/{path}", headers=headers).status_code, 403)

    def test_operations_camera_responses_do_not_expose_raw_stream_credentials(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        secret_stream = "rtsp://camera-user:camera-pass@10.7.0.15:554/live"
        camera = self.client.post(
            "/api/v1/organizations/org-demo/operations/cameras",
            json={"site_id": "site-demo", "name": "Cred Cam", "stream_identifier": secret_stream, "status": "active", "metadata": {}},
            headers=headers,
        )
        self.assertEqual(camera.status_code, 200)
        camera_payload = camera.json()["camera"]
        self.assertNotIn("stream_identifier", camera_payload)
        self.assertEqual(camera_payload["stream_source_type"], "rtsp")
        self.assertIn("RTSP", camera_payload["display_stream_identifier"])
        for leaked in ("camera-user", "camera-pass", "10.7.0.15", "live"):
            self.assertNotIn(leaked, camera_payload["display_stream_identifier"])

        listed = self.client.get("/api/v1/organizations/org-demo/operations/cameras", headers=headers).json()["items"]
        listed_camera = next(item for item in listed if item["id"] == camera_payload["id"])
        self.assertNotIn("stream_identifier", listed_camera)
        catalog = self.client.get("/api/v1/organizations/org-demo/operations/catalog", headers=headers).json()
        catalog_camera = next(item for item in catalog["cameras"] if item["id"] == camera_payload["id"])
        nested_camera = next(item for item in catalog["sites"][0]["cameras"] if item["id"] == camera_payload["id"])
        self.assertNotIn("stream_identifier", catalog_camera)
        self.assertNotIn("stream_identifier", nested_camera)
        for payload in (listed_camera, catalog_camera, nested_camera):
            serialized = str(payload)
            self.assertNotIn("camera-pass", serialized)
            self.assertNotIn("10.7.0.15", serialized)

    def test_operations_mutations_require_permission_and_csrf(self) -> None:
        bad_csrf_headers = {**ORIGIN_HEADERS, settings.csrf_header_name: "bad"}
        good_headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}

        user = self.container.auth_service.repository.get_user_by_email("admin@vigia.local")
        assert user is not None
        original_memberships = list(self.container.auth_service.repository.memberships[user.id])
        self.container.auth_service.repository.memberships[user.id] = [
            MembershipSummary(organization=original_memberships[0].organization, role="auditor_viewer", permissions=original_memberships[0].permissions, active=True)
        ]
        self.assertEqual(self.client.post("/api/v1/organizations/org-demo/operations/sites", json={"name": "Nope"}, headers=good_headers).status_code, 403)
        self.container.auth_service.repository.memberships[user.id] = original_memberships

        self.assertEqual(self.client.post("/api/v1/organizations/org-demo/operations/sites", json={"name": "New Site"}, headers=ORIGIN_HEADERS).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/organizations/org-demo/operations/sites", json={"name": "New Site"}, headers=bad_csrf_headers).status_code, 403)

        site = self.client.post("/api/v1/organizations/org-demo/operations/sites", json={"name": "New Site", "address": "A1", "status": "active"}, headers=good_headers)
        self.assertEqual(site.status_code, 200)
        site_id = site.json()["site"]["id"]
        updated = self.client.patch(f"/api/v1/organizations/org-demo/operations/sites/{site_id}", json={"name": "Updated Site", "address": "B2", "status": "inactive"}, headers=good_headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["site"]["name"], "Updated Site")

        camera = self.client.post("/api/v1/organizations/org-demo/operations/cameras", json={"site_id": site_id, "name": "Cam 2", "stream_identifier": "rtsp://example", "status": "active", "metadata": {"source": "demo"}}, headers=good_headers)
        self.assertEqual(camera.status_code, 200)
        camera_id = camera.json()["camera"]["id"]
        zone = self.client.post("/api/v1/organizations/org-demo/operations/zones", json={"site_id": site_id, "camera_id": camera_id, "zone_type": "access", "polygon_json": {"points": []}, "status": "active"}, headers=good_headers)
        self.assertEqual(zone.status_code, 200)
        zone_id = zone.json()["zone"]["id"]
        self.assertEqual(self.client.patch(f"/api/v1/organizations/org-demo/operations/cameras/{camera_id}", json={"site_id": site_id, "name": "Cam 2B", "status": "inactive"}, headers=good_headers).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/v1/organizations/org-demo/operations/zones/{zone_id}", json={"site_id": site_id, "camera_id": camera_id, "zone_type": "restricted", "polygon_json": {"points": [[0, 0]]}, "status": "inactive"}, headers=good_headers).status_code, 200)

    def test_operations_mutations_reject_cross_tenant_and_nested_mismatch(self) -> None:
        headers = {**ORIGIN_HEADERS, settings.csrf_header_name: self.csrf}
        site = self.client.post("/api/v1/organizations/org-demo/operations/sites", json={"name": "Scoped Site"}, headers=headers)
        self.assertEqual(site.status_code, 200)
        site_id = site.json()["site"]["id"]
        other_site = self.container.operations_repository.create_site("org-other", "Other Site", site_id="site-other")
        other_camera = self.container.operations_repository.create_camera("org-other", other_site.id, "Other Cam", "rtsp://other", camera_id="camera-other")
        self.assertEqual(self.client.patch(f"/api/v1/organizations/org-demo/operations/cameras/{other_camera.id}", json={"site_id": site_id, "name": "Bad", "stream_identifier": "rtsp://bad", "status": "active", "metadata": {}}, headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/organizations/org-demo/operations/zones", json={"site_id": site_id, "camera_id": other_camera.id, "zone_type": "access", "polygon_json": {}, "status": "active"}, headers=headers).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/v1/organizations/org-demo/operations/sites/{site_id}", json={"name": "Scoped Site", "address": None, "status": "active"}, headers={"Origin": "https://evil.example", settings.csrf_header_name: self.csrf}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
