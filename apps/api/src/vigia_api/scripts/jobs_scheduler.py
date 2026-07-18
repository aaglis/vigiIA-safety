from __future__ import annotations

import argparse
import json

from ..container import build_container
from ..services.jobs import OperationalJobsService
from ..services.scheduler import JobScheduler, RedisLockBackend
from ..settings import settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vigia_api.scripts.jobs_scheduler")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--organization-id")
    parser.add_argument("--poll-seconds", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    container = build_container(settings, seed_dev=False)
    jobs = OperationalJobsService(container.edge_worker_service, container.evidence_service, container.incident_repository, app_settings=container.settings)
    redis_backend = None
    if getattr(container.settings, "redis_url", None):
        try:
            from redis import Redis

            redis_backend = Redis.from_url(container.settings.redis_url, decode_responses=True)
            redis_backend.ping()
        except Exception:
            redis_backend = None
    lock_backend = RedisLockBackend(redis_backend) if redis_backend is not None else None
    scheduler = JobScheduler(jobs, lock_backend=lock_backend, app_settings=container.settings, platform_admin_service=container.platform_admin_service)
    if args.once:
        result = scheduler.run_once(organization_id=args.organization_id)
        print(json.dumps({"ran": result.ran, "skipped": result.skipped, "failed": result.failed}, ensure_ascii=False, sort_keys=True))
        return 0
    try:
        scheduler.run_forever(poll_seconds=args.poll_seconds)
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
