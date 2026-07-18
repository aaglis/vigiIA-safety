#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "packages" / "contracts"
PERMISSIONS = CONTRACTS / "permissions" / "permissions.yaml"
EVENTS_DIR = CONTRACTS / "events"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_permissions(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    roles: list[str] = []
    permissions: dict[str, list[str]] = {}
    current_key: str | None = None
    current_roles: list[str] | None = None
    mode = None
    for raw in path.read_text().splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "roles:":
            mode = "roles"
            continue
        if stripped == "permissions:":
            mode = "permissions"
            continue
        if mode == "roles" and stripped.endswith(":") and not stripped.startswith("description"):
            roles.append(stripped[:-1])
            continue
        if mode == "permissions":
            if stripped.startswith("- key:"):
                current_key = stripped.split(":", 1)[1].strip()
                if current_key in permissions:
                    fail(f"duplicate permission key: {current_key}")
                current_roles = []
                permissions[current_key] = current_roles
                continue
            if stripped.startswith("roles:") and current_roles is not None:
                value = stripped.split(":", 1)[1].strip()
                value = value.strip("[]")
                current_roles.extend([item.strip() for item in value.split(",") if item.strip()])
                continue
    return roles, permissions


def validate_permissions() -> None:
    roles, permissions = parse_permissions(PERMISSIONS)
    if len(permissions) != len(set(permissions)):
        fail("duplicate permission keys found")
    known_roles = set(roles)
    for key, assigned in permissions.items():
        for role in assigned:
            if role not in known_roles:
                fail(f"permission {key} references unknown role {role}")


def validate_event_schema(path: Path) -> None:
    schema = json.loads(path.read_text())
    if schema.get("type") != "object":
        fail(f"{path.name}: schema type must be object")
    if schema.get("additionalProperties") is not False:
        fail(f"{path.name}: additionalProperties must be false")
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        fail(f"{path.name}: properties/required missing")
    for req in required:
        if req not in properties:
            fail(f"{path.name}: required field {req} missing from properties")


def validate_event_payloads() -> None:
    edge_src = str(ROOT / "apps" / "edge-worker" / "src")
    if edge_src not in sys.path:
        sys.path.insert(0, edge_src)
    from vigia_edge_worker.config import default_config
    from vigia_edge_worker.heartbeat import build_heartbeat
    from vigia_edge_worker.mock_detector import detect_once
    from vigia_edge_worker.telemetry import TelemetryState

    detection = detect_once(default_config()).to_dict()
    telemetry = TelemetryState(cv_mode="mock", source_type="video", worker_version="test")
    heartbeat = build_heartbeat(default_config(), processed_frames=1, emitted_events=1, telemetry=telemetry, last_error="camera offline", pending_queue=2).to_dict()

    detection_schema = json.loads((EVENTS_DIR / "detection-event.v1.schema.json").read_text())
    heartbeat_schema = json.loads((EVENTS_DIR / "edge-heartbeat.v1.schema.json").read_text())

    for payload, schema, name in [(detection, detection_schema, "detection-event"), (heartbeat, heartbeat_schema, "edge-heartbeat")]:
        props = set(schema.get("properties", {}))
        missing = sorted(set(payload) - props)
        if missing:
            fail(f"{name}: payload keys not covered by schema: {', '.join(missing)}")
        for req in schema.get("required", []):
            if req not in payload:
                fail(f"{name}: required schema field missing in payload: {req}")
    status_props = set(heartbeat_schema["properties"]["status"]["properties"])
    status_missing = sorted(set(heartbeat["status"]) - status_props)
    if status_missing:
        fail(f"edge-heartbeat.status: payload keys not covered by schema: {', '.join(status_missing)}")


def main() -> int:
    validate_permissions()
    for schema in EVENTS_DIR.glob("*.schema.json"):
        validate_event_schema(schema)
    validate_event_payloads()
    print("Validação OK: contratos de permissões e eventos consistentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
