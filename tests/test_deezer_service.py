import os
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock deezloader modules
sys.modules['deezloader'] = MagicMock()
sys.modules['deezloader.deezloader'] = MagicMock()
sys.modules['deezloader.models'] = MagicMock()
sys.modules['deezloader.models.smart'] = MagicMock()

# Setup the mock for DeeLogin
mock_dee_login_class = MagicMock()
sys.modules['deezloader.deezloader'].DeeLogin = mock_dee_login_class

# Now import the service
from services.deezer_service import DeezerService

class TestDeezerService(unittest.TestCase):
    def setUp(self):
        mock_dee_login_class.reset_mock()

    @patch.dict(os.environ, {'DEEZER_ARL': 'dummy_arl'})
    def test_init(self):
        """Test that DeezerService initializes and tries to create DeeLogin client"""
        service = DeezerService()
        self.assertIsNotNone(service.client)
        mock_dee_login_class.assert_called_with(arl='dummy_arl')

    @patch.dict(os.environ, {}, clear=True)
    def test_init_no_arl(self):
        """Test initialization without ARL"""
        # Ensure DEEZER_ARL is definitely not present
        if 'DEEZER_ARL' in os.environ:
            del os.environ['DEEZER_ARL']

        service = DeezerService()
        # Should log error but not crash, client should be None
        self.assertIsNone(service.client)

if __name__ == '__main__':
    unittest.main()
