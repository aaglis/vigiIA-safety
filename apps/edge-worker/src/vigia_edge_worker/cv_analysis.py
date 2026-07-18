"""Lógica pura de verificação de segurança a partir de detecções de objetos.

Recebe caixas já normalizadas (independente do modelo/CV) + o contexto operacional
(zonas com polígono, EPIs exigidos) e decide as VIOLAÇÕES:
  - restricted_intrusion: pessoa dentro de uma zona restrita.
  - ppe_violation: pessoa sem capacete numa zona de EPI.

Sem dependências de OpenCV/YOLO — 100% testável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .geometry import bbox_base_center, bbox_base_center_visible, horizontal_overlap, parse_polygon, point_in_polygon

# Categorias normalizadas que o detector produz a partir das classes do modelo.
CATEGORY_PERSON = "person"
CATEGORY_HELMET = "helmet"
CATEGORY_NO_HELMET = "no_helmet"  # cabeça sem capacete (classe direta do modelo, se houver)

BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class DetectedBox:
    category: str
    confidence: float
    bbox: BBox  # normalizado [0..1]: (x1, y1, x2, y2)


@dataclass(frozen=True)
class Violation:
    event_type: str  # "restricted_intrusion" | "ppe_violation"
    zone_id: str
    confidence: float
    category: str
    bbox: BBox
    metadata: dict[str, Any] = field(default_factory=dict)


def _in_zone(bbox: BBox, polygon) -> bool:
    if not bbox_base_center_visible(bbox):
        return False
    if polygon is None:
        return True  # zona sem geometria vale para o frame inteiro
    cx, cy = bbox_base_center(bbox)
    return point_in_polygon(cx, cy, polygon)


def _has_helmet_on(person: DetectedBox, helmets: list[DetectedBox]) -> bool:
    """True se algum capacete cobre a região da cabeça (terço superior) da pessoa."""
    x1, y1, x2, y2 = person.bbox
    head_bottom = y1 + (y2 - y1) * 0.35
    for helmet in helmets:
        hx1, hy1, hx2, hy2 = helmet.bbox
        head_center_y = (hy1 + hy2) / 2.0
        if head_center_y <= head_bottom and horizontal_overlap(person.bbox, helmet.bbox) > 0.2:
            return True
    return False


def _person_for_head(head: DetectedBox, persons: list[DetectedBox]) -> DetectedBox | None:
    """Associa uma detecção de cabeça à pessoa mais provável.

    A cabeça sem capacete informa o EPI; a zona continua sendo decidida pelos pés/base
    da pessoa. Sem pessoa associada, não inferimos pertencimento à zona de chão.
    """
    hx1, hy1, hx2, hy2 = head.bbox
    head_center_y = (hy1 + hy2) / 2.0
    candidates: list[DetectedBox] = []
    for person in persons:
        x1, y1, x2, y2 = person.bbox
        head_bottom = y1 + (y2 - y1) * 0.45
        if head_center_y <= head_bottom and horizontal_overlap(person.bbox, head.bbox) > 0.2:
            candidates.append(person)
    if not candidates:
        return None
    return max(candidates, key=lambda p: horizontal_overlap(p.bbox, head.bbox))


def _ppe_requires_helmet(required_ppe: list[dict[str, Any]]) -> bool:
    items = " ".join(str(p.get("item", "")).lower() for p in required_ppe)
    if not items:
        return True  # zona de EPI sem item específico => assume capacete
    return any(token in items for token in ("capacete", "helmet", "hardhat", "hard hat", "hard-hat"))


def evaluate_violations(
    boxes: list[DetectedBox],
    zones: list[dict[str, Any]],
    required_ppe: list[dict[str, Any]],
    *,
    head_class_available: bool,
    can_see_helmet: bool = True,
) -> list[Violation]:
    """`can_see_helmet` diz se o modelo carregado tem alguma classe de capacete.

    Sem ela, a zona de EPI NÃO é avaliada: um modelo que não enxerga capacete acusaria
    100% das pessoas de estarem sem ele (a lista de capacetes vem sempre vazia, e
    "nenhum capacete casado" viraria violação). Não se afirma a ausência do que não se
    sabe ver — melhor não reportar nada e sinalizar a incapacidade.
    """
    persons = [b for b in boxes if b.category == CATEGORY_PERSON]
    helmets = [b for b in boxes if b.category == CATEGORY_HELMET]
    bare_heads = [b for b in boxes if b.category == CATEGORY_NO_HELMET]

    restricted_zones = [z for z in zones if str(z.get("zone_type", "")).lower() == "restricted"]
    ppe_zones = [z for z in zones if str(z.get("zone_type", "")).lower() == "ppe"]

    violations: list[Violation] = []

    # Intrusão em zona restrita: qualquer pessoa dentro do polígono.
    for zone in restricted_zones:
        polygon = parse_polygon(zone.get("polygon_json"))
        for person in persons:
            if _in_zone(person.bbox, polygon):
                violations.append(
                    Violation("restricted_intrusion", str(zone.get("id")), person.confidence, CATEGORY_PERSON, person.bbox)
                )

    # EPI (capacete) em zona de EPI.
    for zone in ppe_zones:
        if not can_see_helmet:
            continue
        if not _ppe_requires_helmet(required_ppe):
            continue
        polygon = parse_polygon(zone.get("polygon_json"))
        if head_class_available:
            # Modelo tem classe direta de cabeça-sem-capacete.
            for head in bare_heads:
                person = _person_for_head(head, persons)
                if person is not None and _in_zone(person.bbox, polygon):
                    violations.append(
                        Violation("ppe_violation", str(zone.get("id")), head.confidence, CATEGORY_NO_HELMET, person.bbox, {"ppe_item": "capacete", "head_bbox": head.bbox})
                    )
        else:
            # Modelo tem person + helmet: associa geometricamente.
            for person in persons:
                if not _in_zone(person.bbox, polygon):
                    continue
                if not _has_helmet_on(person, helmets):
                    violations.append(
                        Violation("ppe_violation", str(zone.get("id")), person.confidence, CATEGORY_PERSON, person.bbox, {"ppe_item": "capacete"})
                    )

    return violations
