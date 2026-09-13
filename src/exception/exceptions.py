from src.exception.global_exception_handler import AppError

class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404
    message = "The requested resource was not found."

class AuthError(AppError):
    code = "UNAUTHENTICATED"
    http_status = 401
    message = "Authentication failed."

class RateLimitError(AppError):
    code = "RATE_LIMITED"
    http_status = 429
    message = "Too many requests. Please try again later."

class PermissionError_(AppError):
    code = "PERMISSION_ERROR"
    http_status = 403
    message = "You don't have permission to do that."

class ValidationError_(AppError):
    code = "VALIDATION_ERROR"
    http_status = 400
    message = "The request was invalid."

class InternalServerError_(AppError):
    code = "INTERNAL_SERVER_ERROR"
    http_status = 500
    message = "Something went wrong. Please try again."

class RepositoryError(AppError):
    code = "REPOSITORY_ERROR"
    http_status = 500
    message = "A database operation failed. Please try again."

class TransientError(AppError):
    code = "SERVICE_UNAVAILABLE"
    http_status = 503
    message = "A temporary issue occurred. Please try again shortly."
