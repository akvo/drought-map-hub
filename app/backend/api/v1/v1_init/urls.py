from django.urls import re_path
from api.v1.v1_init.views import (
    health_check,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/health/check",
        health_check,
        name="health_check",
    ),
]
