from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django_q.tasks import async_task
from django_json_widget.widgets import JSONEditorWidget
from .models import SystemUser, Ability
from api.v1.v1_jobs.models import Jobs, JobTypes, JobStatus
from api.v1.v1_users.constants import UserRoleTypes


# Add manage users in admin django
class SystemUserAdmin(UserAdmin):
    site_header = "Manage Users"
    model = SystemUser
    list_display = (
        "email",
        "name",
        "role",
        "email_verified",
    )
    list_filter = (
        "role",
        "email_verified",
    )
    fieldsets = (
        (None, {"fields": ("email", "name", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "role",
                    "email_verified",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "name",
                    "password1",
                    "password2",
                    "role",
                    "technical_working_group",
                ),
            },
        ),
    )
    search_fields = (
        "email",
        "name",
    )
    ordering = ("email",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            obj.generate_reset_password_code()
            if int(request.POST.get("role")[0]) == UserRoleTypes.admin:
                # Automatically set superuser status for admin role
                obj.is_superuser = True
                obj.save(update_fields=["is_superuser"])
            job = Jobs.objects.create(
                type=JobTypes.new_user_password_setup,
                status=JobStatus.on_progress,
            )
            task_id = async_task(
                "api.v1.v1_jobs.job.notify_reset_password",
                obj,
                True,
                hook="api.v1.v1_jobs.job.email_notification_results",
            )
            job.task_id = task_id
            job.save()


class AbilityForm(forms.ModelForm):
    class Meta:
        model = Ability
        fields = "__all__"
        widgets = {
            "conditions": JSONEditorWidget,
        }


class AbilityAdmin(admin.ModelAdmin):
    site_header = "Manage Permissions"
    model = Ability
    form = AbilityForm

    list_display = ("role", "action", "subject", "conditions")
    list_filter = ("role", "action", "subject")
    fieldsets = (
        (None, {"fields": ("role", "action", "subject", "conditions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("role", "action", "subject", "conditions"),
            },
        ),
    )
    search_fields = ("action", "subject")
    ordering = ("role",)


admin.site.register(SystemUser, SystemUserAdmin)
admin.site.register(Ability, AbilityAdmin)
