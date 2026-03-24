from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import engine
from api.routers import eval, experiments, health, messages
from data.schemas.models import Base
from services.monitoring.metrics import instrument_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Converta — LLM Message Optimization Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_app(app)

app.include_router(health.router)
app.include_router(messages.router)
app.include_router(experiments.router)
app.include_router(eval.router)
