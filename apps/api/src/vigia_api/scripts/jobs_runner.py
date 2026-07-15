from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from ..container import build_container
from ..services.jobs import OperationalJobsService
from ..settings import settings


def _parse_now(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vigia_api.scripts.jobs_runner")
    parser.add_argument("job", choices=["offline-workers", "evidence-retention", "notifications", "all"])
    parser.add_argument("--organization-id")
    parser.add_argument("--incident-id")
    parser.add_argument("--threshold-seconds", type=int, default=300)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--reason")
    parser.add_argument("--actor-user-id")
    parser.add_argument("--now")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    container = build_container(settings, seed_dev=False)
    jobs = OperationalJobsService(container.edge_worker_service, container.evidence_service, container.incident_repository)
    now = _parse_now(args.now)
    if args.job == "offline-workers":
        result = jobs.run_offline_workers(organization_id=args.organization_id, threshold_seconds=args.threshold_seconds, now=now)
    elif args.job == "evidence-retention":
        if not args.organization_id:
            raise SystemExit("--organization-id is required for evidence-retention")
        result = jobs.run_evidence_retention(args.organization_id, confirm=args.confirm, actor_user_id=args.actor_user_id, reason=args.reason, now=now)
    elif args.job == "notifications":
        if not args.organization_id:
            raise SystemExit("--organization-id is required for notifications")
        result = jobs.run_notifications(args.organization_id, incident_id=args.incident_id, now=now)
    else:
        result = jobs.run_all(organization_id=args.organization_id, threshold_seconds=args.threshold_seconds, confirm=args.confirm, actor_user_id=args.actor_user_id, reason=args.reason, now=now)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
