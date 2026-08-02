from fastapi import FastAPI
from src.dependencies import lifespan
from fastapi.middleware.cors import CORSMiddleware
from src.paper.routes.routes import paper_router
from src.db.routes.routes import db_router
from src.auth.routes.routes import auth_routes


app = FastAPI(title="QuickPaper AI", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes)
app.include_router(paper_router)
app.include_router(db_router)