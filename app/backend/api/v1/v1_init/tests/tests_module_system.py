from django.test import TestCase, override_settings

from utils.modules import module_enabled
from utils.module_test_base import CoreOnlyTestCase


class ModuleEnabledTest(TestCase):
    @override_settings(DIH_MODULES=None)
    def test_unset_enables_everything(self):
        self.assertTrue(module_enabled("geonode"))
        self.assertTrue(module_enabled("anything"))

    @override_settings(DIH_MODULES=["geonode", "weather"])
    def test_listed_only(self):
        self.assertTrue(module_enabled("geonode"))
        self.assertTrue(module_enabled("weather"))
        self.assertFalse(module_enabled("iks"))

    @override_settings(DIH_MODULES=[])
    def test_empty_disables_everything(self):
        self.assertFalse(module_enabled("geonode"))


class CoreOnlyHarnessTest(CoreOnlyTestCase):
    def test_all_optional_modules_off(self):
        self.assertFalse(module_enabled("geonode"))
        self.assertFalse(module_enabled("weather"))
