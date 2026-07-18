from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ModelManifestError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelManifestEntry:
    filename: str
    version: str
    source: str
    license: str
    sha256: str
    notes: str | None = None


def _default_manifest_path(model_path: str | Path) -> Path:
    return Path(model_path).resolve().parent / "manifest.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ModelManifestError(f"manifest not found: {path}")
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        raise ModelManifestError(f"invalid manifest JSON: {path}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        raise ModelManifestError("manifest must contain a models array")
    return data


def _sha256(path: Path) -> str:
    if not path.exists():
        raise ModelManifestError(f"model file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_model_manifest(model_path: str | Path, manifest_path: str | Path | None = None, version: str | None = None) -> ModelManifestEntry:
    model = Path(model_path)
    manifest = Path(manifest_path) if manifest_path is not None else _default_manifest_path(model)
    data = _load_manifest(manifest)
    filename = model.name
    matches = [item for item in data["models"] if isinstance(item, dict) and item.get("filename") == filename]
    if version is not None:
        matches = [item for item in matches if item.get("version") == version]
    if not matches:
        raise ModelManifestError(f"unknown model: {filename}")
    if len(matches) > 1:
        raise ModelManifestError(f"ambiguous manifest entries for {filename}")
    entry = matches[0]
    for key in ("filename", "version", "source", "license", "sha256"):
        if key not in entry:
            raise ModelManifestError(f"manifest entry missing {key}: {filename}")
    expected = str(entry["sha256"]).lower()
    actual = _sha256(model)
    if actual != expected:
        raise ModelManifestError(f"hash mismatch for {filename}")
    return ModelManifestEntry(filename=str(entry["filename"]), version=str(entry["version"]), source=str(entry["source"]), license=str(entry["license"]), sha256=expected, notes=str(entry.get("notes")) if entry.get("notes") is not None else None)
