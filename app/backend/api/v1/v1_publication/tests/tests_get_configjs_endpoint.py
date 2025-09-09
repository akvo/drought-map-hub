import os
from pathlib import Path
from django.test import TestCase
from django.test.utils import override_settings

config_path = "source/config/config.min.js"


@override_settings(USE_TZ=False, TEST_ENV=True)
class ConfigJS(TestCase):
    def test_config_generation(self):
        if Path(config_path).exists():
            os.remove(config_path)
        self.assertFalse(Path(config_path).exists())
        self.client.get("/api/v1/config.js", follow=True)
        self.assertTrue(Path(config_path).exists())
        os.remove(config_path)
