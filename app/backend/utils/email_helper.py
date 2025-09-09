from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework import serializers
from utils.custom_serializer_fields import CustomChoiceField
from drought_map_hub.settings import EMAIL_FROM, WEBDOMAIN


class EmailTypes:
    verification_email = "verification_email"
    forgot_password = "forgot_password"
    review_completed = "review_completed"
    review_overdue = "review_overdue"
    review_request = "review_request"
    new_user_password_setup = "new_user_password_setup"
    send_feedback = "send_feedback"

    FieldStr = {
        verification_email: "verification_email",
        forgot_password: "forgot_password",
        review_completed: "review_completed",
        review_overdue: "review_overdue",
        review_request: "review_request",
        new_user_password_setup: "new_user_password_setup",
        send_feedback: "send_feedback",
    }


class ListEmailTypeRequestSerializer(serializers.Serializer):
    type = CustomChoiceField(
        choices=list(EmailTypes.FieldStr.keys()), required=True
    )


def email_context(context: dict, type: str):
    if type == EmailTypes.new_user_password_setup:
        context.update(
            {
                "subject": "Welcome to Eswatini Drought Monitor",
                "body": """
                Welcome to Eswatini Drought Monitor platform!
                Before you can start exploring everything.
                Please set up your password using the link below:
                """,
                "cta_text": "Set Up My Password",
                "cta_url": "{0}/reset-password?code={1}".format(
                    WEBDOMAIN, context["reset_password_code"]
                ),
            }
        )
    if type == EmailTypes.verification_email:
        context.update(
            {
                "subject": "Verify Your Email Address",
                "body": """
                We're excited to have you on board. Before you can start
                exploring everything.
                Please click the link below to activate your account:
                """,
                "cta_text": "Verify My Email",
                "cta_url": "{0}/api/v1/email/verify?code={1}".format(
                    WEBDOMAIN, context["verification_code"]
                ),
            }
        )
    if type == EmailTypes.forgot_password:
        context.update(
            {
                "subject": "Reset Your Password",
                "body": """
                We received a password reset request for your account.
                If you did not make the request, please ignore this email.
                Otherwise, you can reset your password using the link below:
                """,
                "cta_text": "Reset My Password",
                "cta_url": "{0}/reset-password?code={1}".format(
                    WEBDOMAIN, context["reset_password_code"]
                ),
            }
        )
    if type == EmailTypes.review_completed:
        context.update(
            {
                "subject": (
                    "Review completed by "
                    "{0} for month {1}".format(
                        context["reviewer_name"],
                        context["year_month"],
                    )
                ),
                "body": (
                    """
                    Dear Admin,
                    {0} has completed the review of
                     the CDI Map for month <b>{1}</b>.
                    """.format(
                        context["reviewer_name"],
                        context["year_month"],
                    )
                ),
                "cta_text": "See the review",
                "cta_url": (
                    "{0}/publications/{1}/reviews/{2}".format(
                        WEBDOMAIN,
                        context["id"],
                        context["review_id"],
                    )
                ),
            }
        )
    if type == EmailTypes.review_overdue:
        context.update(
            {
                "subject": (
                    "We are awaiting for "
                    "you review of the CDI Map for month {0}".format(
                        context["year_month"],
                    )
                ),
                "body": (
                    """
                    Dear {0},
                    The {1} deadline for
                    the CDI Map review for month {2} has passed.
                    Please attend to the submit link below as soon as possible.
                    """.format(
                        context["name"],
                        context["due_date"],
                        context["year_month"],
                    )
                ),
                "cta_text": "Submit review",
                "cta_url": (
                    "{0}/reviews/{1}".format(
                        WEBDOMAIN,
                        context["id"],
                    )
                ),
            }
        )
    if type == EmailTypes.review_request:
        context.update(
            {
                "cta_text": "Submit Review",
                "cta_url": "{0}/reviews/{1}".format(
                    WEBDOMAIN,
                    context["id"],
                ),
            }
        )
    if type == EmailTypes.send_feedback:
        context.update(
            {
                "subject": "Feedback from Eswatini Drought Monitor",
                "body": (
                    """
                    Dear Admin,
                    {0} has sent the following feedback:
                    <br>
                    {1}
                    """.format(
                        context["email"],
                        context["feedback"],
                    )
                ),
            }
        )
    return context


def send_email(
    context: dict,
    type: str,
    path=None,
    content_type=None,
    send=True,
):
    context = email_context(context=context, type=type)
    try:

        email_html_message = render_to_string("email/main.html", context)
        msg = EmailMultiAlternatives(
            "EDM - {0}".format(context.get("subject")),
            "Email plain text",
            EMAIL_FROM,
            context.get("send_to"),
        )
        msg.attach_alternative(email_html_message, "text/html")
        if path:
            msg.attach(Path(path).name, open(path).read(), content_type)
        if send:
            msg.send()
        if not send:
            return email_html_message
    except Exception as ex:
        print("Error", ex)
        print(ex)
