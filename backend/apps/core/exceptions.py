from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def handler(exc, context):
    """Model-level validation errors (e.g. licence quotas raised from signals) become clean 400 responses."""
    if isinstance(exc, DjangoValidationError):
        return Response({"detail": " ".join(exc.messages)}, status=400)
    return exception_handler(exc, context)
