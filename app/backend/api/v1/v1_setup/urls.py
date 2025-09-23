from django.urls import re_path
from api.v1.v1_setup.views import (
    SetupView,
    ManageSetupView,
    OrganizationViewSet,
    BoundingBoxView,
    UserSetupView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/setup/?$",
        SetupView.as_view(),
        name="setup",
    ),
    re_path(
        r"^(?P<version>(v1))/manage-setup/(?P<uuid>[0-9a-f-]{36})/?$",
        ManageSetupView.as_view(),
        name="manage_setup",
    ),
    re_path(
        r"^(?P<version>(v1))/organizations/?$",
        OrganizationViewSet.as_view({
            "get": "list",
            "post": "create"
        }),
        name="organizations",
    ),
    re_path(
        r"^(?P<version>(v1))/organizations/(?P<pk>[0-9]+)",
        OrganizationViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "delete": "destroy"
        }),
        name="organization-detail",
    ),
    re_path(
        r"^(?P<version>(v1))/bbox-setup/?$",
        BoundingBoxView.as_view(),
        name="bbox-setup",
    ),
    re_path(
        r"^(?P<version>(v1))/user-setup/?$",
        UserSetupView.as_view(),
        name="user-setup",
    ),
]
