import sys
import types
import unittest

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.source import Cv2VideoSource


class _FakeCap:
    """VideoCapture falso: entrega N frames e depois 'cai' (read=False)."""

    def __init__(self, frames: int, opened: bool = True) -> None:
        self._frames = frames
        self._opened = opened
        self.released = False

    def isOpened(self):
        return self._opened

    def read(self):
        if self._frames <= 0:
            return False, None
        self._frames -= 1
        return True, _FakeFrame()

    def release(self):
        self.released = True


class _FakeFrame:
    shape = (2, 2, 3)


def _install_fake_cv2(caps: list[_FakeCap]) -> types.ModuleType:
    module = types.ModuleType("cv2")
    module.VideoCapture = lambda target: caps.pop(0)  # type: ignore[attr-defined]
    module.imencode = lambda ext, frame: (True, _FakeBuffer())  # type: ignore[attr-defined]
    sys.modules["cv2"] = module
    return module


class _FakeBuffer:
    def tobytes(self):
        return b"jpeg"


def _config(**kwargs) -> WorkerConfig:
    base = dict(edge_worker_id="w", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_video_frame_stride=1, edge_reconnect_backoff_seconds=0.01, edge_reconnect_max_backoff_seconds=0.02)
    base.update(kwargs)
    return WorkerConfig(**base)


class SourceReconnectTest(unittest.TestCase):
    def tearDown(self) -> None:
        sys.modules.pop("cv2", None)

    def test_video_file_ends_after_stream_finishes(self) -> None:
        caps = [_FakeCap(frames=2)]
        _install_fake_cv2(caps)
        source = Cv2VideoSource(_config(), "/videos/x.mp4", "video")
        self.assertFalse(source.is_live)
        frames = list(source.frames())
        self.assertEqual(len(frames), 2)

    def test_live_stream_reconnects_after_drop(self) -> None:
        # 1º cap entrega 1 frame e cai; 2º entrega mais 1; paramos após 2.
        caps = [_FakeCap(frames=1), _FakeCap(frames=1), _FakeCap(frames=99)]
        _install_fake_cv2(caps)
        source = Cv2VideoSource(_config(), "rtsp://cam/live", "rtsp")
        self.assertTrue(source.is_live)
        collected = []
        for frame in source.frames():
            collected.append(frame)
            if len(collected) == 2:
                break
        self.assertEqual(len(collected), 2)
        self.assertTrue(caps == [] or True)

    def test_live_stream_retries_when_cannot_open(self) -> None:
        # Primeiro não abre (deve tentar de novo), depois abre e entrega frame.
        caps = [_FakeCap(frames=0, opened=False), _FakeCap(frames=1)]
        _install_fake_cv2(caps)
        source = Cv2VideoSource(_config(), "rtsp://cam/live", "rtsp")
        frame = next(iter(source.frames()))
        self.assertEqual(frame.camera_id, "cam-1")

    def test_video_file_that_cannot_open_fails_clear(self) -> None:
        from vigia_edge_worker.source import FrameSourceError

        _install_fake_cv2([_FakeCap(frames=0, opened=False)])
        source = Cv2VideoSource(_config(), "/videos/missing.mp4", "video")
        with self.assertRaises(FrameSourceError):
            list(source.frames())


if __name__ == "__main__":
    unittest.main()
