from django.conf import settings
from django.http import JsonResponse


class SetupMiddleware:
    """
    Middleware to protect certain endpoints with a shared secret header.

    Configuration (in settings.py):
      - SETUP_SECRET_KEY: the secret string. If not set, middleware is a no-op.
      - SETUP_PROTECTED_PATHS: list/tuple of path prefixes to protect
        (e.g. ['/api/v1/setup', '/api/v1/manage-setup']). If not set,
        defaults to ['/api/v1/setup', '/api/v1/manage-setup'].

    The middleware checks the `X-Setup-Secret` header (or HTTP_X_SETUP_SECRET
    in WSGI environ) and returns 403 JSON response if missing/invalid.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.secret = getattr(settings, "SETUP_SECRET_KEY", None)
        self.paths = getattr(
            settings,
            "SETUP_PROTECTED_PATHS",
            ["/api/v1/setup", "/api/v1/manage-setup"],
        )

    def __call__(self, request):
        # If no secret is configured, do nothing
        if not self.secret:
            return self.get_response(request)

        # Check if the request path starts with any protected path
        path = request.path
        for prefix in self.paths:
            if path.startswith(prefix):
                header_value = request.headers.get("X-Setup-Secret") or request.META.get(
                    "HTTP_X_SETUP_SECRET"
                )
                if not header_value or header_value != self.secret:
                    return JsonResponse({"detail": "Forbidden."}, status=403)
                break

        return self.get_response(request)