from django.urls import re_path
from api.v1.v1_setup.views import SetupView

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/setup/?$",
        SetupView.as_view(),
        name="setup",
    ),
    re_path(
        r"^(?P<version>(v1))/manage-setup/(?P<pk>[0-9]+)/?$",
        SetupView.as_view(),
        name="manage_setup",
    ),
]
