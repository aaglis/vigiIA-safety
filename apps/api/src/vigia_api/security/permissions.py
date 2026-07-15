from __future__ import annotations

from ..domain.auth import Permission, PlatformRole

ROLE_PERMISSIONS: dict[str, set[str]] = {
    PlatformRole.PLATFORM_OWNER.value: {
        "org.create",
        "org.suspend",
        "org.manage",
        "org.members.invite",
        "org.members.manage",
        "org.roles.manage",
        "org.security.manage",
        "sites.manage",
        "zones.manage",
        "cameras.manage",
        "rules.manage",
        "workers.manage",
        "workers.register",
        "incidents.read",
        "incidents.write",
        "incidents.acknowledge",
        "incidents.resolve",
        "incidents.dismiss",
        "evidence.read",
        "audit.read",
        "edge.heartbeat.write",
    },
    PlatformRole.PLATFORM_ADMIN.value: {
        "org.create",
        "org.suspend",
        "org.manage",
        "org.members.invite",
        "org.members.manage",
        "org.roles.manage",
        "org.security.manage",
        "sites.manage",
        "zones.manage",
        "cameras.manage",
        "rules.manage",
        "workers.manage",
        "workers.register",
        "incidents.read",
        "incidents.write",
        "incidents.acknowledge",
        "incidents.resolve",
        "incidents.dismiss",
        "evidence.read",
        "audit.read",
        "edge.heartbeat.write",
    },
    PlatformRole.PLATFORM_SUPPORT.value: {"incidents.read", "evidence.read", "audit.read"},
    "org_owner": {"view_dashboard", "org.manage", "org.members.invite", "org.members.manage", "org.roles.manage", "org.security.manage", "sites.manage", "zones.manage", "cameras.manage", "rules.manage", "workers.manage", "workers.register", "incidents.read", "incidents.write", "incidents.acknowledge", "incidents.resolve", "incidents.dismiss", "evidence.read", "audit.read"},
    "org_admin": {"view_dashboard", "org.manage", "org.members.invite", "org.members.manage", "org.roles.manage", "org.security.manage", "sites.manage", "zones.manage", "cameras.manage", "rules.manage", "workers.manage", "workers.register", "incidents.read", "incidents.write", "incidents.acknowledge", "incidents.resolve", "incidents.dismiss", "evidence.read", "audit.read"},
    "manager": {"view_dashboard", "org.members.invite", "workers.manage", "workers.register", "incidents.read", "incidents.write", "incidents.acknowledge", "incidents.resolve", "incidents.dismiss", "evidence.read"},
    "auditor_viewer": {"view_dashboard", "incidents.read", "evidence.read", "audit.read"},
}

ORG_ROLE_ALIASES = {"owner": "org_owner", "admin": "org_admin", "manager": "manager", "auditor": "auditor_viewer", "viewer": "auditor_viewer"}


def role_permissions(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(ORG_ROLE_ALIASES.get(role, role), set()))


def has_permission(role: str, permission: str | Permission) -> bool:
    key = permission.value if isinstance(permission, Permission) else permission
    return key in role_permissions(role)


def can_manage_critical_org_settings(role: str) -> bool:
    return role in {"org_owner", "org_admin", PlatformRole.PLATFORM_OWNER.value, PlatformRole.PLATFORM_ADMIN.value}
