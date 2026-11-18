"""Shared test base for the optional-module system (DIH-2).

``CoreOnlyTestCase`` runs with every optional module disabled. As each
optional app is ported it adds its own assertion here (its surface is absent,
its routes 404) so the core-only contract stays green. Today there is nothing
optional to gate, so the base only pins that everything is off.
"""

from django.test import TestCase, override_settings


@override_settings(DIH_MODULES=[])
class CoreOnlyTestCase(TestCase):
    """All optional modules off; subclasses assert core-only behaviour."""

    pass
