import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class UploadClipMetadataRollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
        os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")

        supabase_module = types.ModuleType("supabase")
        supabase_module.Client = object
        supabase_module.create_client = MagicMock()
        sys.modules["supabase"] = supabase_module

        dotenv_module = types.ModuleType("dotenv")
        dotenv_module.load_dotenv = MagicMock()
        sys.modules["dotenv"] = dotenv_module

        sys.modules.pop("supabase_client", None)
        cls.supabase_client = importlib.import_module("supabase_client")

    def _upload_with_metadata_failure(self, supabase_mock, delete_response):
        supabase_mock.table.return_value.insert.return_value.execute.side_effect = [
            RuntimeError("metadata insert failed: missing column"),
            RuntimeError("metadata insert failed permanently"),
        ]

        with patch.object(self.supabase_client, "supabase", supabase_mock), patch.object(
            self.supabase_client.requests, "post", return_value=FakeResponse(status_code=201)
        ), patch.object(
            self.supabase_client.requests, "delete", return_value=delete_response
        ), patch.object(
            self.supabase_client.os.path, "getsize", return_value=1024
        ), patch.object(
            self.supabase_client.os, "open", unittest.mock.mock_open(read_data=b"clip")
        ):
            with self.assertRaisesRegex(RuntimeError, "metadata insert failed: missing column"):
                self.supabase_client.upload_clip_to_storage(
                    local_path="clip.mp4",
                    user_id="user-1",
                    job_id="job-1",
                )

    def test_metadata_failure_rolls_back_successfully_uploaded_clip(self):
        supabase_mock = MagicMock()
        delete_response = FakeResponse(status_code=200)

        self._upload_with_metadata_failure(supabase_mock, delete_response)

        self.assertEqual(
            supabase_mock.table.return_value.insert.return_value.execute.call_count,
            2,
        )
        self.assertEqual(
            self.supabase_client.requests.delete.call_count,
            1,
        )
        self.supabase_client.requests.delete.assert_called_once_with(
            "https://example.supabase.co/storage/v1/object/clips",
            headers={
                "Authorization": "Bearer test-key",
                "apikey": "test-key",
                "Content-Type": "application/json",
            },
            json={"prefixes": ["user-1/job-1/clip.mp4"]},
        )

    def test_metadata_failure_preserves_error_when_rollback_fails(self):
        supabase_mock = MagicMock()
        delete_response = FakeResponse(status_code=500, text="storage unavailable")

        self._upload_with_metadata_failure(supabase_mock, delete_response)
        self.assertEqual(self.supabase_client.requests.delete.call_count, 1)

    def test_successful_metadata_insert_does_not_delete_clip(self):
        supabase_mock = MagicMock()
        supabase_mock.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch.object(self.supabase_client, "supabase", supabase_mock), patch.object(
            self.supabase_client.requests, "post", return_value=FakeResponse(status_code=201)
        ), patch.object(self.supabase_client.requests, "delete") as delete_mock, patch.object(
            self.supabase_client.os.path, "getsize", return_value=1024
        ), patch.object(
            self.supabase_client.os, "open", unittest.mock.mock_open(read_data=b"clip")
        ):
            result = self.supabase_client.upload_clip_to_storage(
                local_path="clip.mp4",
                user_id="user-1",
                job_id="job-1",
            )

        self.assertEqual(result, "user-1/job-1/clip.mp4")
        delete_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
