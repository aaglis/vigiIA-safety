from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_module_path = Path(__file__).resolve().parent.parent / "src" / "vigia_edge_worker" / "events.py"
_spec = spec_from_file_location("vigia_edge_worker._src_events", _module_path)
assert _spec and _spec.loader
_module = module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

DetectionEvent = _module.DetectionEvent
HeartbeatEvent = _module.HeartbeatEvent
utc_now = _module.utc_now
new_event_id = _module.new_event_id
validate_detection_event = _module.validate_detection_event
validate_heartbeat_event = _module.validate_heartbeat_event
