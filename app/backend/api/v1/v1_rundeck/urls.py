from django.urls import re_path
from api.v1.v1_rundeck.views import (
    SettingsViewSet,
    RundeckProjectsAPI,
    RundeckJobsAPI,
    RundeckExecutionsAPI,
    AdminContactView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/admin/settings",
        SettingsViewSet.as_view({"get": "list", "post": "create"}),
        name="settings",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/setting/(?P<pk>[0-9]+)",
        SettingsViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="settings-details",
    ),
    re_path(
        r"^(?P<version>(v1))/rundeck/projects",
        RundeckProjectsAPI.as_view(),
        name="rundeck-projects"
    ),
    re_path(
        r"^(?P<version>(v1))/rundeck/project/(?P<project>[0-9a-zA-Z_-]+)/jobs",
        RundeckJobsAPI.as_view(),
        name="rundeck-jobs"
    ),
    re_path(
        r"^(?P<version>(v1))/rundeck/job/(?P<job_id>[0-9a-zA-Z_-]+)/execs",
        RundeckExecutionsAPI.as_view(),
        name="rundeck-executions"
    ),
    re_path(
        r"^(?P<version>(v1))/admin/contacts",
        AdminContactView.as_view(),
        name="admin_contacts",
    ),
]
