from django.urls import re_path

from api.v1.v1_datasets.views import AdminDatasetAPI, AdminDatasetPeriodsAPI

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/datasets/(?P<key>[-\w]+)/periods$",
        AdminDatasetPeriodsAPI.as_view(),
        name="admin-dataset-periods",
    ),
    re_path(
        r"^(?P<version>(v1))/datasets/(?P<key>[-\w]+)$",
        AdminDatasetAPI.as_view(),
        name="admin-dataset",
    ),
]
