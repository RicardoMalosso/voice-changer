from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from mods.open_app import open_when_ready


class OpenAppTests(unittest.TestCase):
    def test_opens_full_frontend_when_server_answers(self):
        process = MagicMock()
        process.is_alive.return_value = True
        with (patch("mods.open_app.urlopen") as fetch,
              patch("mods.open_app.open_window", return_value=True) as open_window):
            fetch.return_value.__enter__.return_value = SimpleNamespace(status=200)
            self.assertTrue(open_when_ready(18888, process, "vcclient.exe"))
        fetch.assert_called_once_with("http://localhost:18888/front/", timeout=1)
        open_window.assert_called_once_with("http://localhost:18888/front/", "vcclient.exe")

    def test_does_not_open_window_if_server_exited(self):
        process = MagicMock()
        process.is_alive.return_value = False
        with patch("mods.open_app.open_window") as open_window:
            self.assertFalse(open_when_ready(18888, process, "vcclient.exe"))
        open_window.assert_not_called()
