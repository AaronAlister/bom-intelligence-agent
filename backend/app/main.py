from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.rag.initialization import (
    initialize_rag_vector_store,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize application infrastructure before serving requests.
    """

    app.state.rag_vector_store = (
        initialize_rag_vector_store()
    )

    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router,
    prefix=settings.api_prefix,
)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.app_name,
        "status": "online",
        "docs": "/api/docs",
    }