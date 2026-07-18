import unittest

from vigia_api.domain.incidents import IncidentStatus, parse_detection_event
from vigia_api.container import incident_repository
from vigia_api.services.incidents import InMemoryIncidentRepository
from vigia_api.api.v1 import incidents as incidents_api
from vigia_api.settings import settings


class BrowserRequest:
    method = "POST"
    headers = {"origin": "http://localhost:3000"}
    client = type("Client", (), {"host": "testclient"})()
    url = type("Url", (), {"path": "/api/v1/organizations/org/incidents/action"})()


class IncidentsTest(unittest.TestCase):
    def test_detection_creates_open_incident_and_notification(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(
            parse_detection_event(
                {
                    "organization_id": "org-1",
                    "camera_id": "cam-7",
                    "zone_id": "zone-a",
                    "severity": "high",
                    "summary": "Person near restricted area",
                }
            )
        )
        self.assertEqual(incident.status, IncidentStatus.OPEN)
        self.assertEqual(len(repo.notifications("org-1", incident.id)), 1)
        self.assertEqual(len(repo.audit_logs("org-1", incident.id)), 1)
        self.assertEqual(repo.notifications("org-1", incident.id)[0].status, "queued")

    def test_high_severity_notifications_do_not_leak_sensitive_payload(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "critical", "summary": "Sensitive detail token-abc-123"}))
        attempt = repo.notifications("org-1", incident.id)[0]
        self.assertEqual(attempt.status, "queued")
        self.assertNotIn("re_", str(attempt.payload))
        self.assertNotIn("token-abc-123", str(attempt.payload))

    def test_create_from_detection_is_idempotent_by_org_and_event_id(self) -> None:
        repo = InMemoryIncidentRepository()
        payload = {"organization_id": "org-1", "event_id": "evt-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "high"}

        first = repo.create_from_detection(parse_detection_event(payload))
        second = repo.create_from_detection(parse_detection_event(payload))
        other_event = repo.create_from_detection(parse_detection_event({**payload, "event_id": "evt-2"}))
        other_org = repo.create_from_detection(parse_detection_event({**payload, "organization_id": "org-2"}))

        self.assertEqual(first.id, second.id)
        self.assertNotEqual(first.id, other_event.id)
        self.assertNotEqual(first.id, other_org.id)
        self.assertEqual(len(repo.list_by_organization("org-1")), 2)
        self.assertEqual(len(repo.audit_logs("org-1", first.id)), 1)

    def test_status_transition_appends_audit_log(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(
            parse_detection_event(
                {
                    "organization_id": "org-1",
                    "camera_id": "cam-7",
                    "zone_id": "zone-a",
                    "severity": "medium",
                }
            )
        )
        repo.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "operator")
        self.assertEqual(repo.get("org-1", incident.id).status, IncidentStatus.ACKNOWLEDGED)
        self.assertEqual(len(repo.audit_logs("org-1", incident.id)), 2)

    def test_acknowledge_resolve_and_dismiss_flow_persists_actor_and_reason(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "high"}))
        repo.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "alice")
        repo.transition("org-1", incident.id, IncidentStatus.RESOLVED, "bob", reason="fixed")
        updated = repo.get("org-1", incident.id)
        self.assertEqual(updated.status, IncidentStatus.RESOLVED)
        self.assertEqual(updated.acknowledged_by, "alice")
        self.assertEqual(updated.resolved_by, "bob")
        self.assertEqual(updated.resolution_reason, "fixed")
        self.assertEqual(repo.audit_logs("org-1", incident.id)[-1].metadata["reason"], "fixed")

    def test_dismiss_requires_reason_and_persists_metadata(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "medium"}))
        with self.assertRaises(ValueError):
            repo.transition("org-1", incident.id, IncidentStatus.DISMISSED, "bob")
        dismissed = repo.transition("org-1", incident.id, IncidentStatus.DISMISSED, "bob", reason="false positive")
        self.assertEqual(dismissed.dismissed_by, "bob")
        self.assertEqual(dismissed.dismiss_reason, "false positive")

    def test_invalid_and_terminal_transitions_are_blocked(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "low"}))
        repo.transition("org-1", incident.id, IncidentStatus.RESOLVED, "bob", reason="done")
        with self.assertRaises(ValueError):
            repo.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "alice")
        with self.assertRaises(ValueError):
            repo.transition("org-1", incident.id, IncidentStatus.RESOLVED, "bob", reason="again")

    def test_double_acknowledge_is_invalid(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "low"}))
        repo.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "alice")
        with self.assertRaises(ValueError):
            repo.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "alice")

    def test_api_resolve_and_dismiss_require_reason(self) -> None:
        class CurrentUser:
            def __init__(self) -> None:
                self.user = type("U", (), {"id": "operator-1"})()

        repo = incident_repository
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-2", "camera_id": "cam-9", "zone_id": "zone-b", "severity": "high"}))
        with self.assertRaises(Exception):
            incidents_api.resolve_incident("org-2", incident.id, incidents_api.IncidentReasonIn(reason=""), request=BrowserRequest(), current_user=CurrentUser())
        resolved = incidents_api.resolve_incident("org-2", incident.id, incidents_api.IncidentReasonIn(reason="done"), request=BrowserRequest(), current_user=CurrentUser())
        self.assertEqual(resolved["status"], "resolved")
        self.assertEqual(repo.get("org-2", incident.id).resolved_by, "operator-1")

    def test_cross_tenant_lookup_is_blocked(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-a", "camera_id": "cam-1", "zone_id": "zone-a", "severity": "low"}))
        self.assertEqual(len(repo.list_by_organization("org-b")), 0)
        with self.assertRaises(KeyError):
            repo.get("org-b", incident.id)

    def test_transition_routes_use_current_user_as_actor(self) -> None:
        class CurrentUser:
            def __init__(self) -> None:
                self.user = type("U", (), {"id": "operator-1"})()

        repo = incident_repository
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-7", "zone_id": "zone-a", "severity": "low"}))
        updated = incidents_api.acknowledge_incident("org-1", incident.id, request=BrowserRequest(), current_user=CurrentUser())
        self.assertEqual(updated["status"], "acknowledged")
        self.assertEqual(repo.audit_logs("org-1", incident.id)[-1].actor, "operator-1")
        self.assertEqual(repo.audit_logs("org-1", incident.id)[-1].metadata["previous_status"], "open")
        self.assertEqual(repo.audit_logs("org-1", incident.id)[-1].metadata["next_status"], "acknowledged")

    def test_list_incidents_supports_filters_and_pagination(self) -> None:
        repo = InMemoryIncidentRepository()
        i1 = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "A"}))
        i2 = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-2", "zone_id": "zone-2", "severity": "low", "summary": "B"}))
        i3 = repo.create_from_detection(parse_detection_event({"organization_id": "org-2", "camera_id": "cam-3", "zone_id": "zone-3", "severity": "low", "summary": "C"}))
        repo.transition("org-1", i1.id, IncidentStatus.ACKNOWLEDGED, "actor")
        class Request: app = type("A", (), {"state": type("S", (), {"container": type("C", (), {"incident_repository": repo})()})()})()
        result = incidents_api.list_incidents("org-1", Request(), limit=1, offset=0, severity="high")
        self.assertEqual(result["page_info"]["total"], 1)
        self.assertEqual(result["items"][0]["id"], i1.id)
        self.assertEqual(incidents_api.list_incidents("org-1", Request(), limit=1, offset=1)["page_info"]["offset"], 1)

    def test_list_incidents_orders_by_created_desc_then_id_and_counts_total(self) -> None:
        repo = InMemoryIncidentRepository()
        first = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "event_id": "evt-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "A"}))
        second = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "event_id": "evt-2", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "B"}))
        third = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "event_id": "evt-3", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "C"}))
        class Request: app = type("A", (), {"state": type("S", (), {"container": type("C", (), {"incident_repository": repo})()})()})()
        page1 = incidents_api.list_incidents("org-1", Request(), limit=2, offset=0)
        page2 = incidents_api.list_incidents("org-1", Request(), limit=2, offset=2)
        self.assertEqual(page1["page_info"], {"limit": 2, "offset": 0, "total": 3, "has_next": True})
        self.assertEqual([item["id"] for item in page1["items"]], [third.id, second.id])
        self.assertEqual(page2["page_info"], {"limit": 2, "offset": 2, "total": 3, "has_next": False})
        self.assertEqual([item["id"] for item in page2["items"]], [first.id])
        empty = incidents_api.list_incidents("org-1", Request(), limit=2, offset=99)
        self.assertEqual(empty["items"], [])
        self.assertFalse(empty["page_info"]["has_next"])


if __name__ == "__main__":
    unittest.main()
