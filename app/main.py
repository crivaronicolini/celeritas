from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.agent import lifespan_agent
from app.core.config import settings
from app.db import create_db_and_tables, engine
from app.logging_conf import configure_logging
from app.middleware.wide_logging import WideLoggingMiddleware

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    async with lifespan_agent(app):
        yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(WideLoggingMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
