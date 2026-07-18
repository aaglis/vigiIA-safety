from __future__ import annotations

import argparse
import json
import time
from collections import deque
from uuid import uuid4
from urllib.parse import quote

from .config import default_config
from .client import EdgeApiClient
from .buffer import DetectionBuffer
from .detector import DetectionResult
from .detector_factory import DetectorSelection, build_detector
from .evidence import build_snapshot
from .events import validate_detection_event, validate_heartbeat_event
from .heartbeat import build_heartbeat
from .mock_detector import detect_once
from .rules import AppliedDetection, RuleEngine
from .source import FrameSourceError, build_frame_source
from .telemetry import TelemetryState, sanitize_error, structured_log


def _with_worker_credentials(uri: str | None, config) -> str | None:
    """O servidor de mídia do edge exige credencial para ler a câmera. O worker usa a
    mesma que já tem para falar com a API — assim ele lê só as câmeras atribuídas a ele."""
    if not uri or not config.edge_client_id or not config.edge_api_key:
        return uri
    if not uri.lower().startswith(("rtsp://", "rtmp://")):
        return uri
    scheme, remainder = uri.split("://", 1)
    if "@" in remainder.split("/", 1)[0]:
        return uri
    return f"{scheme}://{quote(config.edge_client_id, safe='')}:{quote(config.edge_api_key, safe='')}@{remainder}"


def _resolve_stream_uri(config, config_payload):
    """Stream da câmera cadastrada (via /me/config) tem prioridade sobre o env."""
    if config_payload:
        cameras = config_payload.get("cameras") or []
        if cameras:
            match = next((c for c in cameras if c.get("id") == config.camera_id), None) or cameras[0]
            return _with_worker_credentials(match.get("stream_identifier") or None, config)
    return None


def _publish_frame_analysis(client, detector, frame) -> None:
    """Best-effort: o overlay ao vivo nunca pode derrubar o pipeline de incidentes."""
    analysis = getattr(detector, "last_analysis", None)
    if client is None or not analysis:
        return
    try:
        client.publish_frame_analysis({"camera_id": frame.camera_id, "timestamp": frame.timestamp, **analysis})
    except Exception as exc:
        structured_log("edge_worker.frame_analysis_failed", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=frame.camera_id, site_id=frame.site_id, organization_id=frame.organization_id, latency_ms=None, result="failed", error=sanitize_error(exc))


def _frame_analysis_interval_seconds(config) -> float:
    fps = max(1.0, min(5.0, float(getattr(config, "edge_frame_analysis_fps", 2.0))))
    return 1.0 / fps


def _refresh_inactive_rules(detector, telemetry) -> None:
    """As classes do modelo só existem depois do primeiro `detect()` (carga lazy), então
    isto é avaliado a cada heartbeat — não uma vez antes do laço, quando o detector ainda
    não sabe o que consegue ver."""
    aviso = "ppe_violation:modelo-sem-classe-de-capacete"
    cego = bool(getattr(detector, "_uses_yolo", lambda: False)()) and not getattr(detector, "can_see_helmet", True)
    if cego and aviso not in telemetry.inactive_rules:
        telemetry.inactive_rules.append(aviso)
    if not cego and aviso in telemetry.inactive_rules:
        telemetry.inactive_rules.remove(aviso)


def _send_heartbeat(config, client, telemetry, processed_frames: int, emitted_events: int, buffer, api_mode: bool, detector=None) -> dict:
    """Monta e envia o heartbeat. Devolve o payload (os testes usam o do fim do ciclo)."""
    if detector is not None:
        _refresh_inactive_rules(detector, telemetry)
    telemetry.processed_frames = processed_frames
    telemetry.emitted_events = emitted_events
    telemetry.pending_queue = buffer.pending_count() if buffer is not None else 0
    heartbeat = build_heartbeat(config, processed_frames=processed_frames, emitted_events=emitted_events, telemetry=telemetry, pending_queue=telemetry.pending_queue, last_error=telemetry.last_error).to_dict()
    validate_heartbeat_event(heartbeat)
    if api_mode and client is not None:
        try:
            client.send_heartbeat(heartbeat)
            structured_log("edge_worker.heartbeat_sent", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=config.camera_id, site_id=config.site_id, organization_id=config.organization_id, latency_ms=telemetry.send_latencies_ms[-1] if telemetry.send_latencies_ms else None, result="ok", pending_queue=telemetry.pending_queue)
        except Exception as exc:
            telemetry.record_error(exc, kind="api")
            structured_log("edge_worker.heartbeat_failed", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=config.camera_id, site_id=config.site_id, organization_id=config.organization_id, latency_ms=None, result="failed", error=exc)
            if buffer is None:
                raise
    return heartbeat


def _build_detection(config, selection, frame, result):
    return {
        "event_id": uuid4().hex,
        "camera_id": frame.camera_id,
        "site_id": frame.site_id,
        "organization_id": frame.organization_id,
        "timestamp": frame.timestamp,
        "event_type": result.event_type,
        "zone_id": result.zone_id,
        "confidence": result.confidence,
        "model_version": result.model_version,
        "severity": "medium",
        "summary": f"Detection in zone {result.zone_id}",
        "worker_id": frame.worker_id,
        "evidence": result.evidence,
        "metadata": {"cv_mode": selection.cv_mode, "source_type": frame.metadata.get("source_type", config.edge_source_type), **result.metadata},
    }


def _evidence_payload(config, frame, upload_path=None, file_id=None, image_bytes=None):
    fid = file_id or uuid4().hex
    snapshot = build_snapshot(fid, frame, upload_path=upload_path, image_bytes=image_bytes)
    return snapshot.to_dict()


def _upload_frame_bytes(client, upload_ref: dict | None, frame, telemetry: TelemetryState | None = None, image_bytes: bytes | None = None) -> dict[str, object]:
    data = image_bytes if image_bytes is not None else frame.image_bytes
    if not upload_ref:
        return {"upload_status": "skipped", "reason": "no_upload_ref"}
    if not data:
        return {"upload_status": "skipped", "reason": "no_frame_bytes"}
    try:
        started = time.perf_counter()
        result = client.upload_evidence_bytes(upload_ref, data, content_type="image/jpeg")
        if telemetry is not None:
            telemetry.record_send_latency((time.perf_counter() - started) * 1000)
        structured_log("edge_worker.evidence_upload_ok", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=frame.camera_id, site_id=frame.site_id, organization_id=frame.organization_id, latency_ms=None, result="ok")
        return {"upload_status": result.get("status", "uploaded")}
    except Exception as exc:
        if telemetry is not None:
            telemetry.record_error(exc, kind="api")
        structured_log("edge_worker.evidence_upload_failed", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=frame.camera_id, site_id=frame.site_id, organization_id=frame.organization_id, latency_ms=None, result="failed", upload_error=sanitize_error(exc))
        return {"upload_status": "failed", "upload_error": sanitize_error(exc)}


def _annotated_evidence_for_results(frame, emitted_results: list[DetectionResult], original_results: list[DetectionResult]) -> bytes | None:
    """Gera um JPEG que desenha exatamente as violações que viraram eventos.

    O detector real pode ter anotado todas as violações brutas do frame antes do cooldown.
    Se alguma delas for suprimida, reaproveitar esse JPEG faria a prova afirmar algo que
    não foi registrado. Por isso a anotação compartilhada do frame é montada aqui, depois
    da decisão de emissão.
    """
    if not emitted_results:
        return None
    shared_jpeg = emitted_results[0].annotated_jpeg
    if shared_jpeg and len(emitted_results) == len(original_results) and all(result.annotated_jpeg == shared_jpeg for result in emitted_results):
        return shared_jpeg
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        if frame.frame is not None:
            image = frame.frame.copy()
        elif frame.image_bytes:
            image = cv2.imdecode(np.frombuffer(frame.image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                return None
        else:
            return None
        height, width = image.shape[:2]
        groups: dict[tuple[float, float, float, float], list[DetectionResult]] = {}
        for result in emitted_results:
            evidence = result.evidence or {}
            raw_bbox = evidence.get("bbox") if isinstance(evidence, dict) else None
            if not isinstance(raw_bbox, (list, tuple)) or len(raw_bbox) != 4:
                continue
            bbox = (
                round(float(raw_bbox[0]), 3),
                round(float(raw_bbox[1]), 3),
                round(float(raw_bbox[2]), 3),
                round(float(raw_bbox[3]), 3),
            )
            groups.setdefault(bbox, []).append(result)
        if not groups:
            return None
        colors = {"ppe_violation": (0, 0, 200), "restricted_intrusion": (0, 140, 220)}
        default_color = (0, 140, 220)
        for bbox, items in groups.items():
            x1, y1, x2, y2 = bbox
            p1 = (int(x1 * width), int(y1 * height))
            p2 = (int(x2 * width), int(y2 * height))
            box_color = colors.get(items[0].event_type, default_color)
            cv2.rectangle(image, p1, p2, box_color, 2)
            for index, item in enumerate(items):
                label_y = max(12, p1[1] - 6 - index * 16)
                cv2.putText(image, item.event_type, (p1[0], label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors.get(item.event_type, default_color), 1)
        ok, buffer = cv2.imencode(".jpg", image)
        return buffer.tobytes() if ok else None
    except Exception:
        if len(emitted_results) == 1 and len(original_results) == 1:
            return emitted_results[0].annotated_jpeg
        return None


def _safe_request_evidence_upload(client, file_id: str, buffer: DetectionBuffer | None = None):
    try:
        return client.request_evidence_upload(file_id=file_id)
    except Exception:
        if buffer is None:
            raise
        return None


def _send_detection(client, detection: dict, buffer: DetectionBuffer | None = None, telemetry: TelemetryState | None = None) -> None:
    if buffer is None:
        client.send_detection(detection)
        return
    event_id = str(detection["event_id"])
    buffer.enqueue(detection)
    try:
        client.send_detection_with_retry(detection, attempts=1)
        buffer.mark_sent(event_id)
    except Exception as exc:
        if telemetry is not None:
            telemetry.record_error(exc, kind="buffer")
        structured_log("edge_worker.detection_send_failed", request_id=getattr(client, "request_id", None), correlation_id=getattr(client, "request_id", None), camera_id=detection.get("camera_id"), site_id=detection.get("site_id"), organization_id=detection.get("organization_id"), latency_ms=None, result="failed", error=exc)
        buffer.mark_failed(event_id, detection, str(exc), attempts=1)


def _drain_buffer(client, buffer: DetectionBuffer, telemetry: TelemetryState | None = None) -> None:
    for buffered in buffer.due():
        try:
            client.send_detection_with_retry(buffered.payload, attempts=1)
            buffer.mark_sent(buffered.event_id)
        except Exception as exc:
            if telemetry is not None:
                telemetry.record_error(exc, kind="buffer")
            buffer.mark_failed(buffered.event_id, buffered.payload, str(exc), attempts=buffered.attempts + 1)


# Câmera ao vivo = loop infinito. O histórico existe para diagnóstico/teste, então é
# limitado: sem isto, cada frame (JPEG) fica retido e o worker morre de OOM em horas.
DIAGNOSTIC_HISTORY_FRAMES = 200


def _run_pipeline(config, selection, detector, source, rules=None, client=None, api_mode: bool = False, buffer: DetectionBuffer | None = None):
    processed_frames = 0
    emitted_events = 0
    history = config.edge_max_frames if config.edge_max_frames is not None else DIAGNOSTIC_HISTORY_FRAMES
    detections = deque(maxlen=history)
    frames = deque(maxlen=history)
    detector_results = deque(maxlen=history)
    telemetry = TelemetryState(cv_mode=selection.cv_mode, source_type=getattr(source, "source_type", config.edge_source_type), worker_version=config.worker_version)
    # Câmera ao vivo = laço infinito: o heartbeat do fim do ciclo NUNCA seria enviado e o
    # worker apareceria offline enquanto trabalha (o job `run_offline_workers` usa
    # last_heartbeat_at). Por isso vai também de tempos em tempos, aqui dentro.
    ultimo_heartbeat = time.monotonic()
    last_frame_analysis_at: float | None = None
    analysis_interval = _frame_analysis_interval_seconds(config)
    for frame in source.frames():
        if api_mode and (time.monotonic() - ultimo_heartbeat) >= config.edge_heartbeat_interval_seconds:
            _send_heartbeat(config, client, telemetry, processed_frames, emitted_events, buffer, api_mode, detector)
            ultimo_heartbeat = time.monotonic()
        infer_started = time.perf_counter()
        results = detector.detect(frame)
        telemetry.record_inference_latency((time.perf_counter() - infer_started) * 1000)
        frames.append(frame)
        detector_results.append(list(results) if results else None)
        processed_frames += 1
        if api_mode and client is not None and getattr(detector, "last_analysis", None):
            now = time.monotonic()
            if last_frame_analysis_at is None or (now - last_frame_analysis_at) >= analysis_interval:
                _publish_frame_analysis(client, detector, frame)
                last_frame_analysis_at = now
        if not results:
            if config.edge_max_frames is not None and processed_frames >= config.edge_max_frames:
                break
            continue
        emitted: list[tuple[DetectionResult, AppliedDetection | None]] = []
        for result in results:
            applied = rules.apply(frame, result) if rules is not None else None
            if rules is not None and applied is None:
                continue
            emitted.append((result, applied))
        if not emitted:
            if config.edge_max_frames is not None and processed_frames >= config.edge_max_frames:
                break
            continue

        emitted_results = [result for result, _ in emitted]
        file_id = uuid4().hex
        annotated = _annotated_evidence_for_results(frame, emitted_results, list(results))
        upload_ref = None
        if api_mode and client is not None:
            upload_ref = _safe_request_evidence_upload(client, file_id, buffer=buffer)
        upload_result = _upload_frame_bytes(client, upload_ref, frame, telemetry=telemetry, image_bytes=annotated) if api_mode and client is not None else {"upload_status": "skipped", "reason": "api_disabled"}
        evidence_payload = _evidence_payload(config, frame, upload_path=upload_ref.get("upload_path") if upload_ref else None, file_id=file_id, image_bytes=annotated)
        evidence_payload.update(upload_result)
        for result, applied in emitted:
            detection = _build_detection(config, selection, frame, result)
            if applied is not None:
                detection["event_type"] = applied.event_type
                detection["severity"] = applied.severity
                detection["summary"] = applied.summary
                detection["zone_id"] = applied.zone_id
                detection["metadata"] = {**detection["metadata"], **applied.metadata}
            detection["evidence"] = dict(evidence_payload)
            validate_detection_event(detection)
            detections.append(detection)
            emitted_events += 1
            if api_mode and client is not None:
                send_started = time.perf_counter()
                _send_detection(client, detection, buffer=buffer, telemetry=telemetry)
                telemetry.record_send_latency((time.perf_counter() - send_started) * 1000)
        if config.edge_max_frames is not None and processed_frames >= config.edge_max_frames:
            break
        if config.edge_frame_interval_seconds > 0:
            time.sleep(config.edge_frame_interval_seconds)
    heartbeat = _send_heartbeat(config, client, telemetry, processed_frames, emitted_events, buffer, api_mode, detector)
    return {"detections": list(detections), "heartbeat": heartbeat, "processed_frames": processed_frames, "emitted_events": emitted_events, "frames": list(frames), "detector_results": list(detector_results), "telemetry": telemetry}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--send-api", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()

    config = default_config()
    selection = DetectorSelection(cv_mode=config.cv_mode, cv_real_enabled=config.cv_real_enabled, cv_real_marker=config.cv_real_marker, cv_real_model_version=config.cv_real_model_version)
    detector = build_detector(config, selection)
    rules = RuleEngine(cooldown_seconds=config.edge_detection_cooldown_seconds)
    buffer = DetectionBuffer(config.edge_buffer_path, max_attempts=config.edge_buffer_max_attempts, backoff_seconds=config.edge_buffer_backoff_seconds) if config.edge_buffer_path else None

    if args.mock and args.once:
        detection = detect_once(config).to_dict()
        heartbeat = build_heartbeat(config, processed_frames=1, emitted_events=1).to_dict()
        validate_detection_event(detection)
        validate_heartbeat_event(heartbeat)
        print(json.dumps(detection, ensure_ascii=False))
        print(json.dumps(heartbeat, ensure_ascii=False))
        return 0

    if args.diagnose:
        diag = {"worker_id": config.edge_worker_id, "cv_mode": config.cv_mode, "source_type": config.edge_source_type, "buffer_path": config.edge_buffer_path, "pending_queue": buffer.pending_count() if buffer is not None else 0, "buffer_enabled": buffer is not None}
        print(json.dumps(diag, ensure_ascii=False, sort_keys=True))
        return 0

    api_mode = bool(args.send_api or (config.edge_api_base_url and config.edge_api_key))
    if api_mode and (not config.edge_api_base_url or not config.edge_api_key):
        parser.error("EDGE_API_BASE_URL and EDGE_API_KEY are required for API mode")

    client_id = config.edge_client_id or config.edge_worker_id
    correlation_id = uuid4().hex
    client = None
    if api_mode:
        assert config.edge_api_base_url is not None and config.edge_api_key is not None
        client = EdgeApiClient(config.edge_api_base_url, client_id, config.edge_api_key, request_id=correlation_id)
        print(json.dumps({"mode": "api", "target": client.describe()}, ensure_ascii=False))
    else:
        print(json.dumps({"mode": "local", "source_type": config.edge_source_type, "cv_mode": config.cv_mode}, ensure_ascii=False))

    def run_once() -> None:
        config_payload = None
        if api_mode and client is not None:
            try:
                config_payload = client.get_config()
                rules.load_context(config_payload)
                load_context = getattr(detector, "load_context", None)
                if callable(load_context):
                    load_context(config_payload)
            except Exception:
                if buffer is None:
                    raise
        source = build_frame_source(config, stream_override=_resolve_stream_uri(config, config_payload))
        if api_mode and client is not None and buffer is not None:
            _drain_buffer(client, buffer, telemetry=TelemetryState(cv_mode=config.cv_mode, source_type=config.edge_source_type, worker_version=config.worker_version))
        result = _run_pipeline(config, selection, detector, source, rules=rules, client=client, api_mode=api_mode, buffer=buffer)
        for detection in result["detections"]:
            structured_log("edge_worker.detection_emitted", request_id=correlation_id, correlation_id=correlation_id, camera_id=detection["camera_id"], site_id=detection["site_id"], organization_id=detection["organization_id"], latency_ms=None, result="ok")
            print(json.dumps(detection, ensure_ascii=False))
        print(json.dumps(result["heartbeat"], ensure_ascii=False))
        sent = ["heartbeat"] + (["detection"] if result["emitted_events"] else [])
        print(json.dumps({"sent": sent, "client_id": client_id, "request_id": correlation_id, "processed_frames": result["processed_frames"], "emitted_events": result["emitted_events"]}, ensure_ascii=False))

    if config.run_once or args.once:
        try:
            run_once()
        except FrameSourceError as exc:
            raise SystemExit(str(exc)) from exc
        return 0

    while True:
        try:
            run_once()
        except FrameSourceError as exc:
            raise SystemExit(str(exc)) from exc
        time.sleep(max(1, config.poll_interval_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
