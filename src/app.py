import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.dependencies import lifespan
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from src.base_settings import settings
from src.exception.global_exception_handler import AppError
from src.exception.exceptions import InternalServerError_
from src.paper.routes.routes import paper_router
from src.db.routes.routes import db_router
from src.auth.routes.routes import auth_routes


app = FastAPI(title="QuickPaper AI", lifespan=lifespan)

# Localhost dev origins are always allowed; production origins come from settings.
dev_origins = [
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

prod_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
origins = dev_origins + prod_origins


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Last-resort catch for anything that isn't an AppError/HTTPException — a genuine bug or
    # unanticipated exception type. Only place in the codebase that will ever see one of these,
    # so print the full traceback rather than just str(exc).
    print(f"[ERROR] Unhandled exception on {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong. Please try again.", "code": InternalServerError_.code},
    )


# Added BEFORE CORSMiddleware so it ends up wrapped INSIDE it (add_middleware inserts each new
# middleware ahead of the previous ones) — otherwise this response would carry no CORS headers,
# same problem as Starlette's own default outer 500 handler.
app.add_middleware(ServerErrorMiddleware, handler=_unhandled_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes)
app.include_router(paper_router)
app.include_router(db_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    print(f"[ERROR] {exc.code}: {exc.message} | context={exc.context}")
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": exc.message, "code": exc.code},
    )