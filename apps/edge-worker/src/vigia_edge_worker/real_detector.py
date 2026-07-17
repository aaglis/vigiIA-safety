from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import WorkerConfig
from .cv_analysis import DetectedBox, evaluate_violations
from .detector import DetectionResult, FrameInput
from .geometry import normalize_bbox


@dataclass(frozen=True)
class RealDetectorConfig:
    enabled: bool = False
    marker: str | None = None
    model_version: str = "real-cv-0"


class RealDetectorError(RuntimeError):
    pass


_PERSON_TOKENS = ("person", "pedestrian", "worker")
_HELMET_TOKENS = ("helmet", "hardhat", "hard hat", "hard-hat", "hard_hat")
_NO_HELMET_TOKENS = ("no-helmet", "no_helmet", "nohelmet", "head", "no hardhat", "no-hardhat")

_SEVERITY_ORDER = {"restricted_intrusion": 0, "ppe_violation": 1}
_VIOLATION_COLORS = {"ppe_violation": (0, 0, 200), "restricted_intrusion": (0, 140, 220)}
_DEFAULT_COLOR = (0, 140, 220)


def _category_for(name: str) -> str | None:
    n = name.lower()
    if any(t in n for t in _NO_HELMET_TOKENS):
        return "no_helmet"
    if any(t in n for t in _HELMET_TOKENS):
        return "helmet"
    if any(t in n for t in _PERSON_TOKENS):
        return "person"
    return None


class RealDetector:
    """Detector de segurança. Com CV_MODEL_PATH definido roda inferência YOLO real
    (EPI capacete + intrusão em zona restrita); sem ele cai num stub offline por
    marcador de bytes, usado só em testes/CI sem as dependências de CV."""

    def __init__(self, config: WorkerConfig, real_config: RealDetectorConfig | None = None) -> None:
        self.config = config
        self.real_config = real_config or RealDetectorConfig()
        self._model: Any = None
        self._class_categories: dict[int, str] = {}
        self._has_no_helmet_class = False
        self._zones: list[dict[str, Any]] = []
        self._required_ppe: list[dict[str, Any]] = []
        self.last_analysis: dict[str, Any] | None = None

    def load_context(self, config_payload: dict[str, Any]) -> None:
        self._zones = list(config_payload.get("zones") or [])
        self._required_ppe = list(config_payload.get("required_ppe") or [])

    def _uses_yolo(self) -> bool:
        return bool(self.config.cv_model_path)

    @property
    def can_see_helmet(self) -> bool:
        """O modelo carregado tem alguma classe de capacete? Derivado das classes reais —
        se fosse uma flag setada só ao carregar o modelo, ficaria dessincronizado sempre
        que as classes viessem por outro caminho."""
        return bool(set(self._class_categories.values()) & {"helmet", "no_helmet"})

    def detect(self, frame: FrameInput) -> list[DetectionResult]:
        if not self.real_config.enabled:
            raise RealDetectorError("real detector disabled: set CV_REAL_ENABLED=1")
        if self._uses_yolo():
            return self._detect_yolo(frame)
        return self._detect_marker(frame)

    def _detect_marker(self, frame: FrameInput) -> list[DetectionResult]:
        if not frame.image_bytes:
            raise RealDetectorError("real detector requires image_bytes frame input")
        marker = self.real_config.marker or frame.metadata.get("cv_marker")
        if not marker:
            raise RealDetectorError("real detector requires CV_REAL_MARKER or frame.metadata.cv_marker")
        if marker.encode("utf-8") not in frame.image_bytes:
            return []
        return [DetectionResult(event_type="real_detection", confidence=0.98, model_version=self.real_config.model_version, zone_id=self.config.zone_id, evidence={"marker": marker}, metadata={"cv_mode": "real", "source": "marker-stub"})]

    def _ensure_model(self) -> Any:
        if self._model is None:
            from ultralytics import YOLO  # type: ignore
            self._model = YOLO(self.config.cv_model_path)
            names = getattr(self._model, "names", {}) or {}
            pairs = names.items() if isinstance(names, dict) else enumerate(names)
            for idx, name in pairs:
                category = _category_for(str(name))
                if category is not None:
                    self._class_categories[int(idx)] = category
            self._has_no_helmet_class = "no_helmet" in self._class_categories.values()
        return self._model

    def _decode(self, frame: FrameInput) -> Any:
        if frame.frame is not None:
            return frame.frame
        if not frame.image_bytes:
            raise RealDetectorError("real detector requires a decoded frame or image_bytes")
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        image = cv2.imdecode(np.frombuffer(frame.image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RealDetectorError("failed to decode frame bytes")
        return image

    def _detect_yolo(self, frame: FrameInput) -> list[DetectionResult]:
        image = self._decode(frame)
        model = self._ensure_model()
        height, width = image.shape[:2]
        prediction = model(image, verbose=False, conf=self.config.cv_confidence_threshold)[0]
        boxes: list[DetectedBox] = []
        raw: list[dict[str, Any]] = []
        for box in prediction.boxes:
            category = self._class_categories.get(int(box.cls[0]))
            if category is None:
                continue
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
            norm = normalize_bbox(x1, y1, x2, y2, width, height)
            boxes.append(DetectedBox(category=category, confidence=confidence, bbox=norm))
            raw.append({"category": category, "confidence": round(confidence, 3), "bbox": [round(v, 4) for v in norm]})

        violations = evaluate_violations(boxes, self._zones, self._required_ppe, head_class_available=self._has_no_helmet_class, can_see_helmet=self.can_see_helmet)
        violations.sort(key=lambda v: (_SEVERITY_ORDER.get(v.event_type, 9), -v.confidence))
        # Sem violação também interessa ao overlay ao vivo: a pessoa em conformidade
        # aparece na tela do cliente. Por isso a análise é registrada antes do early return.
        self.last_analysis = {
            "boxes": raw,
            "violations": [{"event_type": v.event_type, "zone_id": v.zone_id, "confidence": round(v.confidence, 3), "bbox": [round(c, 4) for c in v.bbox]} for v in violations],
        }
        if not violations:
            return []
        annotated = self._annotate(image, violations, width, height)
        results: list[DetectionResult] = []
        for violation in violations:
            results.append(DetectionResult(
                event_type=violation.event_type,
                confidence=round(violation.confidence, 4),
                model_version=self.real_config.model_version,
                zone_id=violation.zone_id,
                evidence={"bbox": [round(v, 4) for v in violation.bbox], "category": violation.category, **violation.metadata},
                metadata={"cv_mode": "real", "model_path": self.config.cv_model_path, "boxes": raw, **violation.metadata},
                annotated_jpeg=annotated,
            ))
        return results

    def _annotate(self, image: Any, violations: list, width: int, height: int) -> bytes | None:
        try:
            import cv2  # type: ignore
            annotated = image.copy()
            # Agrupa por bbox: a mesma pessoa pode gerar várias violações — desenha um
            # retângulo só e empilha os labels, em vez de sobrepô-los no mesmo ponto.
            groups: dict[tuple, list] = {}
            for violation in violations:
                groups.setdefault(tuple(round(coord, 3) for coord in violation.bbox), []).append(violation)
            for bbox, items in groups.items():
                x1, y1, x2, y2 = bbox
                p1 = (int(x1 * width), int(y1 * height))
                p2 = (int(x2 * width), int(y2 * height))
                box_color = _VIOLATION_COLORS.get(items[0].event_type, _DEFAULT_COLOR)
                cv2.rectangle(annotated, p1, p2, box_color, 2)
                for index, item in enumerate(items):
                    label_y = max(12, p1[1] - 6 - index * 16)
                    cv2.putText(annotated, item.event_type, (p1[0], label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, _VIOLATION_COLORS.get(item.event_type, _DEFAULT_COLOR), 1)
            ok, buffer = cv2.imencode(".jpg", annotated)
            return buffer.tobytes() if ok else None
        except Exception:
            return None
