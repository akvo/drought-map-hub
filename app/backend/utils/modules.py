"""Optional-module feature flags (DIH-2).

The generic hub ships a core always-on set of apps; optional apps
(geonode / weather / iks / indicators / risk_level / datasets) stay installed
(D-2: they hold FKs to Administration, so their migrations must always run)
but are switched on/off per deployment via ``DIH_MODULES`` (parsed in settings).

``settings.DIH_MODULES`` is either:
- ``None``  -> var unset, every module enabled (today's behaviour), or
- a list of enabled module names (empty list = everything off).

This is the whole switch. A call site gates itself with a local import (D-3):

    def get_geonode_service():
        if module_enabled("geonode"):
            from api.v1.v1_geonode.services import GeonodeService
            return GeonodeService()
        return None

and a URL is wired only when enabled:

    if module_enabled("geonode"):
        urlpatterns.append(path("api/", include("api.v1.v1_geonode.urls")))

There are no optional apps in the generic repo yet, so nothing is gated today;
the first consumer is the geonode gate in DIH-1. Under WS-3 the flag source
moves from env to ``request.tenant.features`` (MT-7) — this signature stays.
"""

from django.conf import settings


def module_enabled(name: str) -> bool:
    """True when the module is enabled. ``DIH_MODULES`` unset -> all on."""
    modules = getattr(settings, "DIH_MODULES", None)
    return modules is None or name in modules
