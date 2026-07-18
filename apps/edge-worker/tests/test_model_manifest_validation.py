from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.model_manifest import ModelManifestError, verify_model_manifest
from vigia_edge_worker.real_detector import RealDetector, RealDetectorConfig, RealDetectorError


class ModelManifestValidationTest(unittest.TestCase):
    def _write_model(self, dirpath: Path, name: str, content: bytes) -> Path:
        path = dirpath / name
        path.write_bytes(content)
        return path

    def test_verifier_accepts_matching_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = self._write_model(tmp, "ppe-multiclass.pt", b"model-bytes")
            manifest = tmp / "manifest.json"
            manifest.write_text(json.dumps({"version": 1, "models": [{"filename": model.name, "version": "v1", "source": "local", "license": "AGPL-3.0", "sha256": hashlib.sha256(b"model-bytes").hexdigest()}]}))
            entry = verify_model_manifest(model, manifest_path=manifest, version="v1")
            self.assertEqual(entry.filename, model.name)

    def test_verifier_rejects_unknown_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = self._write_model(tmp, "unknown.pt", b"model-bytes")
            manifest = tmp / "manifest.json"
            manifest.write_text(json.dumps({"version": 1, "models": [{"filename": "ppe-multiclass.pt", "version": "v1", "source": "local", "license": "AGPL-3.0", "sha256": hashlib.sha256(b"model-bytes").hexdigest()}]}))
            with self.assertRaises(ModelManifestError):
                verify_model_manifest(model, manifest_path=manifest)

    def test_verifier_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = self._write_model(tmp, "ppe-multiclass.pt", b"good-bytes")
            manifest = tmp / "manifest.json"
            manifest.write_text(json.dumps({"version": 1, "models": [{"filename": model.name, "version": "v1", "source": "local", "license": "AGPL-3.0", "sha256": "0" * 64}]}))
            with self.assertRaises(ModelManifestError):
                verify_model_manifest(model, manifest_path=manifest)

    def test_real_detector_fails_before_yolo_load_on_invalid_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = self._write_model(tmp, "ppe-multiclass.pt", b"model-bytes")
            manifest = tmp / "manifest.json"
            manifest.write_text(json.dumps({"version": 1, "models": [{"filename": model.name, "version": "wrong", "source": "local", "license": "AGPL-3.0", "sha256": hashlib.sha256(b"model-bytes").hexdigest()}]}))
            detector = RealDetector(WorkerConfig(edge_worker_id="w", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", cv_model_path=str(model), cv_model_manifest_path=str(manifest)), RealDetectorConfig(enabled=True))
            with mock.patch.dict("sys.modules", {"ultralytics": mock.Mock(YOLO=mock.Mock(side_effect=AssertionError("YOLO should not be called")))}):
                with self.assertRaises(RealDetectorError):
                    detector._ensure_model()


if __name__ == "__main__":
    unittest.main()
