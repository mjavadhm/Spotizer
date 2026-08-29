import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import sys

# Pre-patch settings and DB stuff before importing main
with patch('backend.config.settings') as mock_settings, \
     patch('sqlalchemy.create_engine'), \
     patch('sqlalchemy.ext.asyncio.create_async_engine'):

    mock_settings.API_ID = 123
    mock_settings.API_HASH = "mock_hash"
    mock_settings.SESSION_NAME = "mock_session"
    mock_settings.MUSIC_CHANNEL_ID = -100123456789
    mock_settings.DEBUG = True
    mock_settings.API_V1_PREFIX = "/api/v1"
    mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
    mock_settings.ASYNC_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/db"

    # Need to manually set these env vars because BaseSettings might read them before we patch settings object?
    # No, we mock the settings OBJECT. But main.py imports 'settings' instance.
    # However, 'backend.database' imports settings and uses it at module level.
    # So we need to ensure 'backend.config' is imported and patched or we mock 'backend.database' entirely.

    with patch('backend.database.init_db', new_callable=AsyncMock), \
         patch('backend.database.close_db', new_callable=AsyncMock), \
         patch('backend.services.telegram_client.telegram_service.start', new_callable=AsyncMock), \
         patch('backend.services.telegram_client.telegram_service.stop', new_callable=AsyncMock):

        # We also need to patch DownloadModel init because it creates DB connection
        with patch('models.download_model.DownloadModel.__init__', return_value=None):
            from backend.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            class TestStreamEndpoints(unittest.TestCase):

                def setUp(self):
                    # We need to patch the download_model instance in stream.py
                    self.mock_download_model_patch = patch('backend.routers.stream.download_model')
                    self.mock_download_model = self.mock_download_model_patch.start()

                    self.mock_telegram_service_patch = patch('backend.routers.stream.telegram_service')
                    self.mock_telegram_service = self.mock_telegram_service_patch.start()

                def tearDown(self):
                    self.mock_download_model_patch.stop()
                    self.mock_telegram_service_patch.stop()

                def test_stream_track_success(self):
                    # Mock DB response
                    self.mock_download_model.get_track_by_deezer_id_quality.return_value = {
                        'track_id': 1,
                        'message_id': 100,
                        'channel_id': -1001,
                        'file_name': 'test.mp3'
                    }

                    # Mock Telethon stream
                    async def mock_stream_gen():
                        yield b"chunk1"
                        yield b"chunk2"

                    self.mock_telegram_service.get_file_stream = AsyncMock(return_value=mock_stream_gen())

                    response = client.get("/api/v1/stream/1?quality=MP3_320")

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['content-type'], 'audio/mpeg')
                    self.assertEqual(response.content, b"chunk1chunk2")

                    self.mock_download_model.get_track_by_deezer_id_quality.assert_called_with(0, 1, "MP3_320")
                    self.mock_telegram_service.get_file_stream.assert_called_with(100, -1001)

                def test_stream_track_not_found_db(self):
                    self.mock_download_model.get_track_by_deezer_id_quality.return_value = None

                    response = client.get("/api/v1/stream/999")

                    self.assertEqual(response.status_code, 404)
                    self.assertIn("Track not found", response.json()['detail'])

                def test_stream_track_no_message_id(self):
                    self.mock_download_model.get_track_by_deezer_id_quality.return_value = {
                        'track_id': 1,
                        'message_id': None, # Missing
                        'channel_id': -1001
                    }

                    response = client.get("/api/v1/stream/1")

                    self.assertEqual(response.status_code, 404)

                def test_download_track_success(self):
                    self.mock_download_model.get_track_by_deezer_id_quality.return_value = {
                        'track_id': 1,
                        'message_id': 100,
                        'channel_id': -1001,
                        'file_name': 'song.mp3'
                    }

                    async def mock_stream_gen():
                        yield b"data"

                    self.mock_telegram_service.get_file_stream = AsyncMock(return_value=mock_stream_gen())

                    response = client.get("/api/v1/download/1")

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers['content-type'], 'application/octet-stream')
                    self.assertIn('attachment; filename="song.mp3"', response.headers['content-disposition'])

            if __name__ == '__main__':
                unittest.main()
