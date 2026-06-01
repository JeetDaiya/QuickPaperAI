from fastapi import FastAPI
from server.dependencies import lifespan
from fastapi.middleware.cors import CORSMiddleware
from server.routes.paper_routes import paper_router
from server.routes.db_routes import db_router


app = FastAPI(title="QuickPaper AI", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(paper_router)
app.include_router(db_router)