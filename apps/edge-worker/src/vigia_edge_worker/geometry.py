"""Geometria pura (sem dependências de CV) para associar detecções a zonas.

Convenção: polígonos de zona e pontos de bounding box são expressos em coordenadas
NORMALIZADAS [0..1] relativas ao frame, para independerem da resolução da câmera.
"""
from __future__ import annotations

from typing import Any, Sequence


Point = tuple[float, float]


def parse_polygon(polygon_json: Any) -> list[Point] | None:
    """Extrai a lista de pontos normalizados de um polygon_json de zona.

    Aceita {"type": "polygon", "points": [[x, y], ...]} ou {"points": [...]}.
    Retorna None quando não há geometria (zona aplica ao frame inteiro).
    """
    if not isinstance(polygon_json, dict):
        return None
    raw_points = polygon_json.get("points")
    if not isinstance(raw_points, (list, tuple)) or len(raw_points) < 3:
        return None
    points: list[Point] = []
    for entry in raw_points:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            points.append((float(entry[0]), float(entry[1])))
        elif isinstance(entry, dict) and "x" in entry and "y" in entry:
            points.append((float(entry["x"]), float(entry["y"])))
    return points if len(points) >= 3 else None


def point_in_polygon(x: float, y: float, polygon: Sequence[Point]) -> bool:
    """Ray casting: True se (x, y) está dentro do polígono (bordas contam como dentro)."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
            if x <= x_cross:
                inside = not inside
        j = i
    return inside


def normalize_bbox(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> tuple[float, float, float, float]:
    w = float(width) or 1.0
    h = float(height) or 1.0
    return (x1 / w, y1 / h, x2 / w, y2 / h)


def bbox_base_center(bbox_norm: tuple[float, float, float, float]) -> Point:
    """Centro da base do bbox (pés da pessoa) — melhor referência para 'está na zona do chão'."""
    x1, y1, x2, y2 = bbox_norm
    return ((x1 + x2) / 2.0, y2)


def bbox_center(bbox_norm: tuple[float, float, float, float]) -> Point:
    x1, y1, x2, y2 = bbox_norm
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def horizontal_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Fração de sobreposição horizontal do bbox b sobre a largura de a (0..1)."""
    ax1, _, ax2, _ = a
    bx1, _, bx2, _ = b
    inter = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    a_width = max(1e-9, ax2 - ax1)
    return inter / a_width
