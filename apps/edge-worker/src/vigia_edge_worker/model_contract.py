from __future__ import annotations

import json
import pickletools
import re
import sys
import zipfile
from contextlib import suppress
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


_PERSON_TOKENS = ("person", "pedestrian", "worker")
_HELMET_TOKENS = ("helmet", "hardhat", "hard hat", "hard-hat", "hard_hat")
_NO_HELMET_TOKENS = ("no-helmet", "no_helmet", "nohelmet", "head", "no hardhat", "no-hardhat")

_ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\- ]{1,64}")


def _category_for(name: str) -> str | None:
    n = name.lower()
    if any(t in n for t in _NO_HELMET_TOKENS):
        return "no_helmet"
    if any(t in n for t in _HELMET_TOKENS):
        return "helmet"
    if any(t in n for t in _PERSON_TOKENS):
        return "person"
    return None


def _iter_strings_from_pickle(data: bytes) -> Iterable[str]:
    try:
        for opcode, arg, _pos in pickletools.genops(data):
            if isinstance(arg, str):
                yield arg
    except Exception:
        pass


def _extract_names_from_pickle(data: bytes) -> list[str]:
    """Extract YOLO class names from a pickle stream without executing it.

    Torch/Ultralytics checkpoints persist `names` as a plain dict in `data.pkl`.
    We intentionally read only values from that dict. A broad string scan is unsafe
    for the product contract because regular checkpoint metadata contains words
    like `head` and `workers`, which would otherwise be mistaken for PPE/person
    classes.
    """
    with suppress(Exception):
        ops = list(pickletools.genops(data))
        for index, (_opcode, arg, _pos) in enumerate(ops):
            if arg != "names":
                continue

            # Find the dict payload that follows the `names` key.
            dict_index = next((i for i in range(index + 1, len(ops)) if ops[i][0].name == "EMPTY_DICT"), None)
            if dict_index is None:
                continue
            mark_index = next((i for i in range(dict_index + 1, len(ops)) if ops[i][0].name == "MARK"), None)
            payload_start = mark_index if mark_index is not None else dict_index

            names: list[str] = []
            pending_int_key = False
            for opcode, value, _ in ops[payload_start + 1:]:
                if opcode.name in {"SETITEM", "SETITEMS"}:
                    return names
                if opcode.name in {"BININT", "BININT1", "BININT2", "INT", "LONG"} and isinstance(value, int):
                    pending_int_key = True
                    continue
                if pending_int_key and isinstance(value, str):
                    names.append(value)
                    pending_int_key = False
                    continue
                if opcode.name not in {"BINPUT", "LONG_BINPUT", "MEMOIZE"}:
                    pending_int_key = False
    return []


def _iter_strings_from_bytes(data: bytes) -> Iterable[str]:
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    for match in _ASCII_TOKEN_RE.finditer(text):
        yield match.group(0)


def _read_blob_metadata(path: Path) -> tuple[list[str], list[str], list[str]]:
    class_names: list[str] = []
    strings: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        return class_names, strings, [f"file not found: {path}"]

    blob = path.read_bytes()
    chunks: list[tuple[str, bytes]] = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                try:
                    chunks.append((name, zf.read(name)))
                except Exception as exc:
                    warnings.append(f"failed to read zip member {name}: {exc}")
    else:
        chunks.append((path.name, blob))

    for name, chunk in chunks:
        if name.endswith(".pkl"):
            class_names.extend(_extract_names_from_pickle(chunk))
        picked = list(_iter_strings_from_pickle(chunk))
        strings.extend(picked)
        if not picked:
            strings.extend(_iter_strings_from_bytes(chunk))
        if name.lower().endswith((".txt", ".json", ".yaml", ".yml")):
            continue

    return class_names, strings, warnings


def _normalize_classes(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    classes: list[str] = []
    for value in values:
        normalized = value.strip().strip("'\"")
        if not normalized:
            continue
        category = _category_for(normalized)
        if category is None:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        classes.append(normalized)
    return classes


@dataclass(frozen=True)
class ModelContractReport:
    model: str
    classes: list[str]
    categories: list[str]
    supports_restricted_intrusion: bool
    supports_ppe_helmet: bool
    supports_product_contract: bool
    license: str | None
    warnings: list[str]


def inspect_model_contract(model_path: str | Path) -> ModelContractReport:
    path = Path(model_path)
    class_names, strings, warnings = _read_blob_metadata(path)

    classes = _normalize_classes(class_names)
    categories = sorted({c for c in (_category_for(x) for x in classes) if c})
    license_value = next((s for s in strings if "agpl-3.0" in s.lower()), None)
    if license_value is None:
        license_value = next((s for s in strings if "license" in s.lower() or "licen" in s.lower()), None)

    supports_restricted_intrusion = "person" in categories
    supports_ppe_helmet = bool({"helmet", "no_helmet"} & set(categories))
    supports_product_contract = {"person", "helmet", "no_helmet"}.issubset(set(categories))

    if not path.exists():
        warnings.append("model file is missing")
    if not zipfile.is_zipfile(path):
        warnings.append("model is not a zip container; inspection is heuristic only")
    if not classes:
        warnings.append("no mappable classes found in model names metadata")
    if "person" not in categories:
        warnings.append("missing person class for restricted intrusion")
    if not supports_ppe_helmet:
        warnings.append("missing helmet/no_helmet class for PPE contract")

    return ModelContractReport(
        model=str(path),
        classes=classes,
        categories=categories,
        supports_restricted_intrusion=supports_restricted_intrusion,
        supports_ppe_helmet=supports_ppe_helmet,
        supports_product_contract=supports_product_contract,
        license=license_value,
        warnings=warnings,
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print(json.dumps({"error": "usage: python -m vigia_edge_worker.model_contract <model.pt>"}, ensure_ascii=False), file=sys.stderr)
        return 1
    report = inspect_model_contract(args[0])
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
    return 0 if report.supports_product_contract and not report.warnings else 1


if __name__ == "__main__":
    raise SystemExit(main())
