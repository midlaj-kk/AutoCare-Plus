from rest_framework.views import exception_handler
from rest_framework.response import Response


def _extract_message(exc, response):
    detail = getattr(exc, "detail", None)
    if detail:
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict):
            for field, msgs in detail.items():
                if isinstance(msgs, list) and len(msgs) > 0:
                    return str(msgs[0])
                return str(msgs)
            return "Validation failed"
        if isinstance(detail, list) and len(detail) > 0:
            return str(detail[0])
    return response.status_text if hasattr(response, "status_text") else "Error occurred"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "success": False,
            "message": _extract_message(exc, response),
            "errors": response.data if isinstance(response.data, dict) else {},
        }
        return response

    from apps.service_jobs.services import InvalidTransitionError
    from apps.inventory.services import InsufficientStockError
    from core.services import HasActiveDependentsError

    if isinstance(exc, InvalidTransitionError):
        return Response(
            {"success": False, "message": str(exc), "errors": {}}, status=409
        )
    if isinstance(exc, InsufficientStockError):
        return Response(
            {"success": False, "message": str(exc), "errors": {}}, status=409
        )
    if isinstance(exc, HasActiveDependentsError):
        return Response(
            {"success": False, "message": str(exc), "errors": {}}, status=409
        )

    return Response(
        {
            "success": False,
            "message": "An unexpected error occurred.",
            "errors": {},
        },
        status=500,
    )
