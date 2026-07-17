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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    notas: str = ""


@dataclass
class Resultado:
    amostra: Amostra
    pessoas_detectadas: int
    sem_capacete_detectados: int
    acusou_violacao_epi: bool
    latencia_ms: float


def carregar_dataset(caminho: Path) -> tuple[dict[str, Any], list[Amostra]]:
    manifest = json.loads(caminho.read_text(encoding="utf-8"))
    amostras = [
        Amostra(
            id=s["id"],
            file=s["file"],
            pessoas_esperadas=int(s["pessoas_esperadas"]),
            pessoas_sem_capacete=int(s["pessoas_sem_capacete"]),
            ha_violacao_epi=bool(s["ha_violacao_epi"]),
            notas=s.get("notas", ""),
        )
        for s in manifest["samples"]
    ]
    return manifest, amostras


def avaliar(dataset: Path, modelo: str, confianca: float = 0.4) -> dict[str, Any]:
    manifest, amostras = carregar_dataset(dataset)
    raiz = dataset.parent

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
        "zones": [{"id": "zone-eval", "site_id": "site-eval", "zone_type": "ppe", "polygon_json": {}}],
        "required_ppe": [{"item": "capacete"}],
    })

    # Aquecimento: a carga do modelo é lazy (1º detect) e levava ~9s, contaminando a
    # latência do primeiro frame e a média. Sem isto, o número medido é "carregar o
    # modelo", não "inferir um frame".
    if amostras:
        primeiro = (raiz / Path(amostras[0].file).name if not (raiz / amostras[0].file).exists() else raiz / amostras[0].file).read_bytes()
        detector.detect(FrameInput(camera_id="cam-eval", site_id="site-eval", organization_id="org-eval", timestamp="2026-01-01T00:00:00Z", image_bytes=primeiro, metadata={"source_type": "warmup"}))

    resultados: list[Resultado] = []
    for amostra in amostras:
        bytes_imagem = (raiz / Path(amostra.file).name if not (raiz / amostra.file).exists() else raiz / amostra.file).read_bytes()
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
        resultados.append(
            Resultado(
                amostra=amostra,
                pessoas_detectadas=sum(1 for b in caixas if b["category"] == "person"),
                sem_capacete_detectados=sum(1 for b in caixas if b["category"] == "no_helmet"),
                acusou_violacao_epi=any(v.event_type == "ppe_violation" for v in violacoes),
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
    f1 = (2 * precisao * recall / (precisao + recall)) if (precisao and recall) else None

    pessoas_esperadas = sum(r.amostra.pessoas_esperadas for r in resultados)
    pessoas_detectadas = sum(r.pessoas_detectadas for r in resultados)
    latencias = [r.latencia_ms for r in resultados]

    return {
        "dataset": manifest.get("version"),
        "modelo": modelo,
        "confianca_minima": confianca,
        "amostras": len(resultados),
        "epi_por_frame": {
            "verdadeiro_positivo": vp,
            "falso_positivo": fp,
            "falso_negativo": fn,
            "verdadeiro_negativo": vn,
            "precisao": round(precisao, 3) if precisao is not None else None,
            "recall": round(recall, 3) if recall is not None else None,
            "f1": round(f1, 3) if f1 is not None else None,
        },
        "contagem_de_pessoas": {
            "esperadas": pessoas_esperadas,
            "detectadas": pessoas_detectadas,
            "diferenca": pessoas_detectadas - pessoas_esperadas,
        },
        "latencia_ms": {
            "media": round(sum(latencias) / len(latencias), 1) if latencias else None,
            "maxima": round(max(latencias), 1) if latencias else None,
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
        "limitacoes": manifest.get("limitacoes_conhecidas", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede a CV real contra frames anotados.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--conf", type=float, default=0.4)
    args = parser.parse_args()

    relatorio = avaliar(args.dataset, args.model, args.conf)
    print(json.dumps(relatorio, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
