from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256

from .detector import FrameInput


@dataclass(frozen=True)
class EvidenceSnapshot:
    file_id: str
    size: int
    sha256_hex: str
    frame_timestamp: str
    source_type: str
    upload_path: str | None = None

    def to_dict(self) -> dict:
        return {key: value for key, value in asdict(self).items() if value is not None}


def build_snapshot(file_id: str, frame: FrameInput, upload_path: str | None = None) -> EvidenceSnapshot:
    data = frame.image_bytes or b""
    return EvidenceSnapshot(file_id=file_id, size=len(data), sha256_hex=sha256(data).hexdigest(), frame_timestamp=frame.timestamp, source_type=str(frame.metadata.get("source_type", "mock")), upload_path=upload_path)
