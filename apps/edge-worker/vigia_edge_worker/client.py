from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_module_path = Path(__file__).resolve().parent.parent / "src" / "vigia_edge_worker" / "client.py"
_spec = spec_from_file_location("vigia_edge_worker._src_client", _module_path)
assert _spec and _spec.loader
_module = module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)
setattr(sys.modules["vigia_edge_worker"], "_src_client", _module)

EdgeApiClient = _module.EdgeApiClient
