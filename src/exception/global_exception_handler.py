class AppError(Exception):
    code: str = "INTERNAL_SERVER_ERROR"
    http_status: int = 500
    message: str = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None, **context) -> None:
        self.message = message or self.message
        self.context = context
        super().__init__(self.message)
