from fastapi import FastAPI
from src.dependencies import lifespan
from fastapi.middleware.cors import CORSMiddleware
from src.base_settings import settings
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