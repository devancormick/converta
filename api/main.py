from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

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
    description="Rewrites consumer-facing loan messages using LLMs, gates outputs through quality classifiers, and measures lift via A/B experiments.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def https_redirect(request: Request, call_next):
    if request.headers.get("x-forwarded-proto") == "http":
        url = request.url.replace(scheme="https")
        return RedirectResponse(url=str(url), status_code=301)
    return await call_next(request)


instrument_app(app)

app.include_router(health.router)
app.include_router(messages.router)
app.include_router(experiments.router)
app.include_router(eval.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    with open("static/dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())
