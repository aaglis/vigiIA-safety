#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path('.')
EXCLUDED_DIRS = {
    '.git', '.github', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '__pycache__', 'node_modules', 'dist', 'build', '.venv', 'venv',
    # Artefatos gerados por testes (bundles minificados dão falso positivo).
    'playwright-report', 'test-results',
    # Config local de ferramenta do dev, fora do versionamento.
    '.claude', '.agents',
}
EXCLUDED_FILES = {
    '.env.example',
    'infra/compose/docker-compose.dev.yml',
    'docs/security/secret-management-policy.md',
    'docs/security/secret-handling-checklist.md',
    'docs/deployment/secret-handling-checklist.md',
    'docs/deployment/local-compose.md',
    'docs/deployment/ci.md',
    'README.md',
    'scripts/check-secrets.sh',
}
TEXT_EXTENSIONS = {
    '.env', '.ini', '.json', '.md', '.py', '.sh', '.toml', '.ts', '.tsx',
    '.txt', '.yaml', '.yml', '.js', '.jsx', '.css', '.html', '.dockerfile',
}
SENSITIVE_NAMES = re.compile(
    r'(?i)\b(jwt_secret|refresh_token_secret|secret_key|password|api_key|access_key|token|private_key|resend_api_key|minio_secret_key|edge_worker_api_key)\b'
)
ASSIGNMENT = re.compile(r'''(?ix)
    (?P<name>[A-Z0-9_]*(?:SECRET|PASSWORD|API_KEY|ACCESS_KEY|TOKEN|PRIVATE_KEY)[A-Z0-9_]*)
    \s*[:=]\s*
    (?P<value>[^#\n]+)
''')
PLACEHOLDER_MARKERS = (
    'dev-only', 'change-me', 'example', 'placeholder', 'todo', 'replace-me',
    'test', 'vigia', 'localhost', '127.0.0.1', 'smtp.dev.local', 'dev-client-id',
    'dev-api-key', '<not-configured>', '<invalid', '***', '${', '$$'
)
PRIVATE_KEY_MARKER = '-----BEGIN '


def is_text_candidate(path: Path) -> bool:
    if path.name in {'Dockerfile', 'docker-compose.dev.yml'}:
        return True
    return path.suffix.lower() in TEXT_EXTENSIONS


def is_excluded(path: Path) -> bool:
    rel = path.as_posix()
    if rel in EXCLUDED_FILES:
        return True
    if 'tests' in path.parts:
        return True
    return any(part in EXCLUDED_DIRS for part in path.parts)


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"\'').lower()
    if not normalized or normalized in {'true', 'false', 'none', 'null'}:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


findings: list[str] = []
for path in ROOT.rglob('*'):
    if not path.is_file() or is_excluded(path) or not is_text_candidate(path):
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if PRIVATE_KEY_MARKER in stripped:
            findings.append(f'{path}:{line_number}: private key marker')
            continue
        match = ASSIGNMENT.search(stripped)
        if not match:
            continue
        name = match.group('name')
        value = match.group('value').split('#', 1)[0].strip().rstrip(',')
        normalized_value = value.strip().strip('"\'').lower()
        if normalized_value in {'str', 'string', 'int', 'bool', 'dict', 'list', 'none', 'null'}:
            continue
        if any(stripped.startswith(prefix) for prefix in ('def ', 'async def ', 'class ', 'interface ', 'type ')):
            continue
        if any(token in value for token in ('os.environ', 'getenv(', 'settings.', 'self.', 'request.', 'payload.', 'Field(')):
            continue
        if path.suffix.lower() in {'.md', '.txt'}:
            continue
        if path.suffix.lower() in {'.py', '.ts', '.tsx', '.js', '.jsx'} and not value.startswith(('"', "'")):
            continue
        if SENSITIVE_NAMES.search(name) and not is_placeholder(value):
            findings.append(f'{path}:{line_number}: suspicious {name}')

if findings:
    print('Possíveis segredos reais encontrados fora da allowlist:', file=sys.stderr)
    for item in findings:
        print(f'- {item}', file=sys.stderr)
    sys.exit(1)

print('Validação OK: varredura simples de segredos sem achados fora da allowlist.')
PY
