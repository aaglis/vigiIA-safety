"""Mede a acurácia da visão computacional REAL.

Por que este arquivo existe: o `evaluation.py` antigo instanciava o `RealDetector` **sem**
`cv_model_path`, então media o stub de bytes-marcador — um `grep`, não o YOLO. E o
"dataset" eram arquivos `.txt`. As métricas ~1.0 que ele produzia não diziam nada sobre
detecção.

O que medimos aqui é a **decisão do produto**, em nível de frame: "há alguém sem capacete
neste quadro?" e "quantas pessoas há?". Não é mAP de bbox — mAP avalia o modelo; isto
avalia o que vira (ou não vira) incidente para o cliente.

Uso:
    python -m vigia_edge_worker.evaluation_real \\
        --dataset datasets/cv-real/v1/manifest.json \\
        --model /models/ppe-multiclass.pt
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import WorkerConfig
from .detector import FrameInput
from .real_detector import RealDetector, RealDetectorConfig


@dataclass
class Amostra:
    id: str
    file: str
    pessoas_esperadas: int
    pessoas_sem_capacete: int
    ha_violacao_epi: bool
    pessoas_com_capacete: int = 0
    scenario: str = ""
    tags: list[str] | None = None
    notas: str = ""


@dataclass
class DatasetSample:
    id: str
    image: Path
    labels: Path | None = None
    pessoas_esperadas: int = 0
    pessoas_sem_capacete: int = 0
    pessoas_com_capacete: int = 0
    ha_violacao_epi: bool = False
    scenario: str = ""
    tags: list[str] | None = None
    notas: str = ""


@dataclass
class Resultado:
    amostra: DatasetSample
    pessoas_detectadas: int
    sem_capacete_detectados: int
    acusou_violacao_epi: bool
    acusou_intrusao_restrita: bool
    latencia_ms: float


def _scenario_summary_name(sample: DatasetSample) -> str:
    return sample.scenario or "default"


def _metric_summary(tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if (precision is not None and recall is not None and (precision + recall)) else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "f1": round(f1, 3) if f1 is not None else None,
    }


def _coverage_summary(resultados: list[Resultado]) -> dict[str, Any]:
    scenarios = Counter(_scenario_summary_name(r.amostra) for r in resultados)
    helmet_samples = sum(1 for r in resultados if r.amostra.pessoas_com_capacete > 0)
    no_helmet_samples = sum(1 for r in resultados if r.amostra.pessoas_sem_capacete > 0)
    empty_samples = sum(1 for r in resultados if r.amostra.pessoas_esperadas == 0)
    return {
        "total_samples": len(resultados),
        "helmet_samples": helmet_samples,
        "no_helmet_samples": no_helmet_samples,
        "empty_samples": empty_samples,
        "scenarios": dict(sorted(scenarios.items())),
    }


def check_report_thresholds(report: dict[str, Any], *, min_samples: int = 0, min_helmet_samples: int = 0, min_empty_samples: int = 0, min_ppe_recall: float = 0.0) -> list[str]:
    failures: list[str] = []
    coverage = report.get("coverage_summary", {})
    ppe = report.get("ppe_violation", {})
    if int(coverage.get("total_samples", 0)) < min_samples:
        failures.append(f"sample_count<{min_samples}")
    if int(coverage.get("helmet_samples", 0)) < min_helmet_samples:
        failures.append(f"helmet_samples<{min_helmet_samples}")
    if int(coverage.get("empty_samples", 0)) < min_empty_samples:
        failures.append(f"empty_samples<{min_empty_samples}")
    recall = ppe.get("recall")
    if recall is None or float(recall) < min_ppe_recall:
        failures.append(f"ppe_recall<{min_ppe_recall}")
    return failures


def _category_for(label: str) -> str | None:
    n = label.lower()
    if any(t in n for t in ("no-helmet", "no_helmet", "nohelmet", "no-hardhat", "no hardhat", "no_hardhat")):
        return "no_helmet"
    if any(t in n for t in ("helmet", "hardhat", "hard hat", "hard-hat")):
        return "helmet"
    if any(t in n for t in ("person", "pedestrian", "worker")):
        return "person"
    return None


def _parse_yaml_value(value: str) -> Any:
    value = value.strip().strip('"\'')
    if value.startswith("[") and value.endswith("]"):
        return [item.strip().strip('"\'') for item in value[1:-1].split(",") if item.strip()]
    if value.startswith("{") and value.endswith("}"):
        items: dict[str, str] = {}
        for part in value[1:-1].split(","):
            if not part.strip():
                continue
            if ":" not in part:
                raise ValueError(f"unsupported inline YAML mapping item: {part}")
            key, val = part.split(":", 1)
            items[key.strip().strip('"\'')] = val.strip().strip('"\'')
        return items
    return value


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("-"):
            if current_key is None:
                raise ValueError(f"unsupported YAML list item without parent key: {raw}")
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(_parse_yaml_value(line[1:].strip()))
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if current_key is None:
                raise ValueError(f"unsupported YAML indentation without parent key: {raw}")
            stripped = line.strip()
            if stripped.startswith("-"):
                if not isinstance(data.get(current_key), list):
                    data[current_key] = []
                data[current_key].append(_parse_yaml_value(stripped[1:].strip()))
                continue
            if ":" in stripped:
                if not isinstance(data.get(current_key), dict):
                    data[current_key] = {}
                key, value = stripped.split(":", 1)
                data[current_key][key.strip().strip('"\'')] = _parse_yaml_value(value)
                continue
            raise ValueError(f"unsupported YAML line: {raw}")
            continue
        if ":" not in line:
            raise ValueError(f"unsupported YAML line: {raw}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            current_key = key
            data[key] = []
            continue
        current_key = None
        data[key] = _parse_yaml_value(value)
    return data


def _normalize_names(names: Any) -> list[str]:
    if isinstance(names, dict):
        numeric_keys = [int(str(key)) for key in names if str(key).isdigit()]
        if numeric_keys and len(numeric_keys) == len(names):
            ordered = [""] * (max(numeric_keys) + 1)
            for key, value in names.items():
                ordered[int(str(key))] = str(value)
            return ordered
        return [str(value) for _, value in sorted(names.items(), key=lambda item: str(item[0]))]
    if isinstance(names, list):
        return [str(name) for name in names]
    if isinstance(names, str) and names:
        return [names]
    return []


def _resolve_image_path(root: Path, rel: str) -> Path:
    p = root / rel
    if p.exists():
        return p
    alt = root / Path(rel).name
    if alt.exists():
        return alt
    return p


def _yolo_label_path(image_path: Path, dataset_root: Path) -> Path:
    try:
        rel = image_path.relative_to(dataset_root)
    except ValueError:
        rel = image_path
    parts = list(rel.parts)
    if "images" in parts:
        idx = parts.index("images")
        return (dataset_root / Path(*parts[:idx], "labels", *parts[idx + 1 :])).with_suffix(".txt")
    return image_path.with_suffix(".txt")


def _parse_yolo_labels(label_path: Path) -> list[str]:
    labels: list[str] = []
    if not label_path.exists():
        return labels
    for line in label_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if not parts:
            continue
        labels.append(parts[0])
    return labels


def carregar_dataset(caminho: Path, splits: Iterable[str] | None = None) -> tuple[dict[str, Any], list[DatasetSample], str]:
    if caminho.name == "data.yaml" or caminho.suffix in {".yml", ".yaml"}:
        data = _parse_simple_yaml(caminho)
        root_value = str(data.get("path") or ".")
        root_path = Path(root_value)
        dataset_root = root_path if root_path.is_absolute() else caminho.parent / root_path
        names = _normalize_names(data.get("names"))
        all_subsets = {k: data.get(k) for k in ("train", "val", "valid", "test") if data.get(k)}
        requested_splits = {s.strip() for s in (splits or []) if s and s.strip()}
        if requested_splits:
            missing = requested_splits - set(all_subsets)
            if missing:
                raise ValueError(f"requested split(s) not found in data.yaml: {sorted(missing)}")
            subsets = {k: v for k, v in all_subsets.items() if k in requested_splits}
        else:
            subsets = all_subsets
        if not subsets:
            raise ValueError("data.yaml must define train/val/test or valid paths")
        samples: list[DatasetSample] = []
        for split, rel in subsets.items():
            split_path = _resolve_image_path(dataset_root, str(rel))
            if split_path.is_dir():
                images = sorted([p for p in split_path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}])
            else:
                images = [split_path]
            for image in images:
                label_path = _yolo_label_path(image, dataset_root)
                labels = _parse_yolo_labels(label_path)
                categories = [c for c in (_category_for(names[int(i)] if str(i).isdigit() and int(i) < len(names) else str(i)) for i in labels) if c]
                expected_people = sum(1 for c in categories if c == "person")
                expected_no_helmet = sum(1 for c in categories if c == "no_helmet")
                expected_helmet = sum(1 for c in categories if c == "helmet")
                samples.append(DatasetSample(
                    id=f"{split}:{image.stem}",
                    image=image,
                    labels=label_path,
                    pessoas_esperadas=expected_people,
                    pessoas_sem_capacete=expected_no_helmet,
                    pessoas_com_capacete=expected_helmet,
                    ha_violacao_epi=expected_no_helmet > 0,
                    scenario=split,
                    tags=[split],
                ))
        manifest = {
            "version": "yolo-data.yaml",
            "mode": "yolo-dataset",
            "source": str(caminho),
            "dataset_root": str(dataset_root),
            "names": names,
            "splits": list(subsets.keys()),
            "limitacoes_conhecidas": [
                "ppe_violation é medido por frame a partir de classes no_helmet/no-hardhat; não é mAP de bbox.",
                "restricted_intrusion_proxy mede presença de pessoa em zona restrita de quadro inteiro; não valida geometria de zona real sem anotações de polígono.",
            ],
        }
        return manifest, samples, "yolo"

    manifest = json.loads(caminho.read_text(encoding="utf-8"))
    amostras = [
        DatasetSample(
            id=s["id"],
            image=caminho.parent / s["file"],
            pessoas_esperadas=int(s["pessoas_esperadas"]),
            pessoas_sem_capacete=int(s["pessoas_sem_capacete"]),
            pessoas_com_capacete=int(s.get("pessoas_com_capacete", 0)),
            ha_violacao_epi=bool(s["ha_violacao_epi"]),
            scenario=str(s.get("scenario", "")),
            tags=list(s.get("tags", [])) if s.get("tags") is not None else None,
            notas=s.get("notas", ""),
        )
        for s in manifest["samples"]
    ]
    return manifest, amostras, "manifest"


def avaliar(dataset: Path, modelo: str, confianca: float = 0.4, splits: Iterable[str] | None = None) -> dict[str, Any]:
    manifest, amostras, modo = carregar_dataset(dataset, splits=splits)
    raiz = dataset.parent if dataset.name != "data.yaml" else dataset.parent

    config = WorkerConfig(
        edge_worker_id="eval",
        organization_id="org-eval",
        site_id="site-eval",
        camera_id="cam-eval",
        zone_id="zone-eval",
        cv_model_path=modelo,
        cv_confidence_threshold=confianca,
    )
    detector = RealDetector(config, RealDetectorConfig(enabled=True, model_version=Path(modelo).name))
    # Zona de EPI cobrindo o quadro inteiro: aqui medimos a DETECÇÃO, não a geometria.
    # Misturar as duas esconderia de qual delas veio o erro.
    detector.load_context({
        "zones": [
            {"id": "zone-eval-restricted", "site_id": "site-eval", "zone_type": "restricted", "polygon_json": {}},
            {"id": "zone-eval-ppe", "site_id": "site-eval", "zone_type": "ppe", "polygon_json": {}},
        ],
        "required_ppe": [{"item": "capacete"}],
    })

    if not amostras:
        raise ValueError("dataset has no samples")

    # Aquecimento: a carga do modelo é lazy (1º detect) e levava ~9s, contaminando a latência.
    primeiro = amostras[0].image.read_bytes()
    detector.detect(FrameInput(camera_id="cam-eval", site_id="site-eval", organization_id="org-eval", timestamp="2026-01-01T00:00:00Z", image_bytes=primeiro, metadata={"source_type": "warmup"}))

    resultados: list[Resultado] = []
    for amostra in amostras:
        bytes_imagem = amostra.image.read_bytes()
        frame = FrameInput(
            camera_id="cam-eval",
            site_id="site-eval",
            organization_id="org-eval",
            timestamp="2026-01-01T00:00:00Z",
            image_bytes=bytes_imagem,
            metadata={"source_type": "dataset", "sample_id": amostra.id},
        )
        inicio = time.perf_counter()
        violacoes = detector.detect(frame)
        latencia = (time.perf_counter() - inicio) * 1000

        analise = detector.last_analysis or {}
        caixas = analise.get("boxes", [])
        detected_counts = Counter(b["category"] for b in caixas)
        resultados.append(
            Resultado(
                amostra=amostra,
                pessoas_detectadas=detected_counts.get("person", 0),
                sem_capacete_detectados=detected_counts.get("no_helmet", 0),
                acusou_violacao_epi=any(v.event_type == "ppe_violation" for v in violacoes),
                acusou_intrusao_restrita=any(v.event_type == "restricted_intrusion" for v in violacoes),
                latencia_ms=latencia,
            )
        )

    # Decisão de EPI por frame (é o que vira incidente).
    vp = sum(1 for r in resultados if r.amostra.ha_violacao_epi and r.acusou_violacao_epi)
    fp = sum(1 for r in resultados if not r.amostra.ha_violacao_epi and r.acusou_violacao_epi)
    fn = sum(1 for r in resultados if r.amostra.ha_violacao_epi and not r.acusou_violacao_epi)
    vn = sum(1 for r in resultados if not r.amostra.ha_violacao_epi and not r.acusou_violacao_epi)

    precisao = vp / (vp + fp) if (vp + fp) else None
    recall = vp / (vp + fn) if (vp + fn) else None
    f1 = (2 * precisao * recall / (precisao + recall)) if (precisao is not None and recall is not None and (precisao + recall)) else None

    pessoas_esperadas = sum(r.amostra.pessoas_esperadas for r in resultados)
    pessoas_detectadas = sum(r.pessoas_detectadas for r in resultados)
    latencias = [r.latencia_ms for r in resultados]

    pessoa_tp = sum(1 for r in resultados if r.amostra.pessoas_esperadas > 0 and r.acusou_intrusao_restrita)
    pessoa_fp = sum(1 for r in resultados if r.amostra.pessoas_esperadas == 0 and r.acusou_intrusao_restrita)
    pessoa_fn = sum(1 for r in resultados if r.amostra.pessoas_esperadas > 0 and not r.acusou_intrusao_restrita)
    pessoa_tn = sum(1 for r in resultados if r.amostra.pessoas_esperadas == 0 and not r.acusou_intrusao_restrita)
    no_helmet_tp = sum(1 for r in resultados if r.amostra.pessoas_sem_capacete > 0 and r.sem_capacete_detectados > 0)
    no_helmet_fp = sum(1 for r in resultados if r.amostra.pessoas_sem_capacete == 0 and r.sem_capacete_detectados > 0)
    no_helmet_fn = sum(1 for r in resultados if r.amostra.pessoas_sem_capacete > 0 and r.sem_capacete_detectados == 0)
    no_helmet_tn = sum(1 for r in resultados if r.amostra.pessoas_sem_capacete == 0 and r.sem_capacete_detectados == 0)
    ppe_tn = vn

    por_scenario: dict[str, list[Resultado]] = {}
    for resultado in resultados:
        por_scenario.setdefault(_scenario_summary_name(resultado.amostra), []).append(resultado)

    scenario_metrics = {
        scenario: {
            "sample_count": len(items),
            "epi_violation": _metric_summary(
                sum(1 for r in items if r.amostra.ha_violacao_epi and r.acusou_violacao_epi),
                sum(1 for r in items if not r.amostra.ha_violacao_epi and r.acusou_violacao_epi),
                sum(1 for r in items if r.amostra.ha_violacao_epi and not r.acusou_violacao_epi),
                sum(1 for r in items if not r.amostra.ha_violacao_epi and not r.acusou_violacao_epi),
            ),
            "restricted_intrusion_proxy": _metric_summary(
                sum(1 for r in items if r.amostra.pessoas_esperadas > 0 and r.acusou_intrusao_restrita),
                sum(1 for r in items if r.amostra.pessoas_esperadas == 0 and r.acusou_intrusao_restrita),
                sum(1 for r in items if r.amostra.pessoas_esperadas > 0 and not r.acusou_intrusao_restrita),
                sum(1 for r in items if r.amostra.pessoas_esperadas == 0 and not r.acusou_intrusao_restrita),
            ),
        }
        for scenario, items in sorted(por_scenario.items())
    }

    return {
        "dataset": manifest.get("version"),
        "dataset_mode": modo,
        "modelo": modelo,
        "confianca_minima": confianca,
        "amostras": len(resultados),
        "coverage_summary": _coverage_summary(resultados),
        "epi_por_frame": {
            **_metric_summary(vp, fp, fn, vn),
        },
        "epi_por_scenario": scenario_metrics,
        "contagem_de_pessoas": {
            "esperadas": pessoas_esperadas,
            "detectadas": pessoas_detectadas,
            "diferenca": pessoas_detectadas - pessoas_esperadas,
        },
        "contagem_no_helmet": {
            "esperadas": sum(r.amostra.pessoas_sem_capacete for r in resultados),
            "detectadas": sum(r.sem_capacete_detectados for r in resultados),
        },
        "latencia_ms": {
            "media": round(sum(latencias) / len(latencias), 1) if latencias else None,
            "maxima": round(max(latencias), 1) if latencias else None,
            "p95": round(sorted(latencias)[max(0, int(len(latencias) * 0.95) - 1)], 1) if latencias else None,
        },
        "restricted_intrusion_proxy": {
            "observacao": "Proxy por frame: pessoa presente vs restricted_intrusion quando a zona cobre o quadro inteiro; não é benchmark geométrico de zonas anotadas.",
            "tp": pessoa_tp,
            "fp": pessoa_fp,
            "fn": pessoa_fn,
            "tn": pessoa_tn,
        },
        "no_helmet_detection_por_frame": {
            "tp": no_helmet_tp,
            "fp": no_helmet_fp,
            "fn": no_helmet_fn,
            "tn": no_helmet_tn,
        },
        "ppe_violation": {
            **_metric_summary(vp, fp, fn, ppe_tn),
        },
        "por_amostra": [
            {
                "id": r.amostra.id,
                "pessoas": f"{r.pessoas_detectadas}/{r.amostra.pessoas_esperadas}",
                "epi_esperado": r.amostra.ha_violacao_epi,
                "epi_detectado": r.acusou_violacao_epi,
                "acertou": r.amostra.ha_violacao_epi == r.acusou_violacao_epi,
                "latencia_ms": round(r.latencia_ms, 1),
            }
            for r in resultados
        ],
        "metadados_dataset": manifest,
        "limitacoes": manifest.get("limitacoes_conhecidas", []) if isinstance(manifest, dict) else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede a CV real contra frames anotados.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--conf", type=float, default=0.4)
    parser.add_argument("--split", action="append", choices=["train", "val", "valid", "test"], help="Para data.yaml, limita a avaliação a um split. Pode repetir.")
    parser.add_argument("--min-samples", type=int, default=0)
    parser.add_argument("--min-helmet-samples", type=int, default=0)
    parser.add_argument("--min-empty-samples", type=int, default=0)
    parser.add_argument("--min-ppe-recall", type=float, default=0.0)
    args = parser.parse_args()

    relatorio = avaliar(args.dataset, args.model, args.conf, splits=args.split)
    failures = check_report_thresholds(
        relatorio,
        min_samples=args.min_samples,
        min_helmet_samples=args.min_helmet_samples,
        min_empty_samples=args.min_empty_samples,
        min_ppe_recall=args.min_ppe_recall,
    )
    if failures:
        print(json.dumps({"status": "failed", "reasons": failures}, ensure_ascii=False))
        return 1
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
