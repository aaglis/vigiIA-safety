import unittest

from vigia_api.domain.auth import PlatformRole
from vigia_api.security.permissions import ROLE_PERMISSIONS, can_manage_critical_org_settings, has_permission, role_permissions
from vigia_api.services.incidents import InMemoryIncidentRepository
from vigia_api.domain.incidents import parse_detection_event
from vigia_api.services.auth import AuthService


class RbacTest(unittest.TestCase):
    def test_permission_matrix_blocks_manager_critical_actions(self) -> None:
        self.assertTrue(has_permission("manager", "incidents.read"))
        self.assertFalse(has_permission("manager", "org.suspend"))
        self.assertFalse(can_manage_critical_org_settings("manager"))
        self.assertTrue(can_manage_critical_org_settings("org_admin"))

    def test_platform_roles_align_with_read_scope(self) -> None:
        self.assertIn("org.create", role_permissions(PlatformRole.PLATFORM_ADMIN.value))
        self.assertNotIn("org.suspend", role_permissions(PlatformRole.PLATFORM_SUPPORT.value))

    def test_role_permissions_are_returned_verbatim_from_me(self) -> None:
        service = AuthService()
        tokens, _, _ = service.login("admin@vigia.local", "change-me-dev")
        me_payload = service.me(tokens.access_token)
        self.assertEqual(me_payload["active_permissions"], sorted(role_permissions("owner")))
        for role in ("org_owner", "org_admin", "manager", "auditor_viewer"):
            self.assertEqual(sorted(role_permissions(role)), sorted(ROLE_PERMISSIONS[role]))

    def test_incident_repo_enforces_organization_boundaries(self) -> None:
        repo = InMemoryIncidentRepository()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-a", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high"}))
        with self.assertRaises(KeyError):
            repo.get("org-b", incident.id)
        self.assertEqual(len(repo.list_by_organization("org-b")), 0)


if __name__ == "__main__":
    unittest.main()
