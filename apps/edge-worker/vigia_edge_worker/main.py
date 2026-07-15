from pathlib import Path
import sys

_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from vigia_edge_worker.main import main as _main  # type: ignore


if __name__ == "__main__":
    raise SystemExit(_main())
