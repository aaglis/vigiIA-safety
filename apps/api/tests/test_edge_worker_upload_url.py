import unittest

from vigia_api.container import build_container


class EdgeWorkerUploadUrlTest(unittest.TestCase):
    def test_request_evidence_upload_returns_upload_url_when_storage_available(self) -> None:
        container = build_container(repository_backend="memory", seed_dev=False)
        worker, api_key = container.edge_worker_service.register_worker("org-1", "site-1", "worker", ["cam-1"])
        result = container.edge_worker_service.request_evidence_upload(worker.client_id, api_key, "file-1")
        self.assertIn("upload_path", result)
        self.assertIn("upload_url", result)


if __name__ == "__main__":
    unittest.main()
