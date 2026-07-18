from __future__ import annotations

import pickle
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from vigia_edge_worker.model_contract import inspect_model_contract, main


def _make_fake_pt(path: Path, names: dict[int, str], license_text: str = "AGPL-3.0") -> None:
    payload = pickle.dumps({"names": names, "license": license_text}, protocol=4)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("best/data.pkl", payload)


class ModelContractTest(unittest.TestCase):
    def test_contract_passes_for_person_helmet_no_helmet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.pt"
            _make_fake_pt(path, {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"})
            report = inspect_model_contract(path)
            self.assertTrue(report.supports_product_contract)
            self.assertTrue(report.supports_restricted_intrusion)
            self.assertTrue(report.supports_ppe_helmet)
            self.assertIn("Person", report.classes)
            self.assertIn("AGPL-3.0", report.license or "")
            self.assertEqual(report.warnings, [])

    def test_contract_fails_without_person(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.pt"
            _make_fake_pt(path, {0: "Hardhat", 1: "NO-Hardhat"})
            report = inspect_model_contract(path)
            self.assertFalse(report.supports_product_contract)
            self.assertFalse(report.supports_restricted_intrusion)
            self.assertTrue(report.supports_ppe_helmet)
            self.assertTrue(any("person" in w.lower() for w in report.warnings))

    def test_contract_fails_without_ppe_helmet_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.pt"
            _make_fake_pt(path, {0: "Person"})
            report = inspect_model_contract(path)
            self.assertFalse(report.supports_product_contract)
            self.assertTrue(report.supports_restricted_intrusion)
            self.assertFalse(report.supports_ppe_helmet)
            self.assertTrue(any("helmet" in w.lower() for w in report.warnings))

    def test_contract_ignores_non_class_metadata_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.pt"
            payload = pickle.dumps({
                "names": {0: "Mask"},
                "module": "ultralytics.nn.modules.head Detect",
                "workers": "workers",
            }, protocol=4)
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("best/data.pkl", payload)

            report = inspect_model_contract(path)

            self.assertFalse(report.supports_product_contract)
            self.assertEqual(report.classes, [])
            self.assertNotIn("head", report.classes)
            self.assertNotIn("workers", report.classes)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok_path = Path(tmp) / "ok.pt"
            bad_path = Path(tmp) / "bad.pt"
            _make_fake_pt(ok_path, {0: "Person", 1: "Hardhat", 2: "NO-Hardhat"})
            _make_fake_pt(bad_path, {0: "Hardhat", 1: "NO-Hardhat"})
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(ok_path)]), 0)
            with redirect_stdout(StringIO()):
                self.assertEqual(main([str(bad_path)]), 1)


if __name__ == "__main__":
    unittest.main()
