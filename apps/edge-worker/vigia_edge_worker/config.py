from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_module_path = Path(__file__).resolve().parent.parent / "src" / "vigia_edge_worker" / "config.py"
_spec = spec_from_file_location("vigia_edge_worker._src_config", _module_path)
assert _spec and _spec.loader
_module = module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

WorkerConfig = _module.WorkerConfig
default_config = _module.default_config
