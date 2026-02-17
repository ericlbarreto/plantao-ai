"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.controllers.message_controller import router as message_router
from app.api.controllers.schedule_controller import router as schedule_router
from app.common.config import settings
from app.common.tracing import setup_tracing
from app.db.models import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# Initialise tracing before app is created
setup_tracing()

app = FastAPI(
    title="Plantão AI",
    description="AI-powered shift-offer analyser for doctors.",
    version="0.1.0",
    lifespan=lifespan,
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Register routers
app.include_router(message_router, tags=["message"])
app.include_router(schedule_router, tags=["schedule"])


@app.get("/health")
async def health():
    """Simple health-check endpoint."""
    return {"status": "ok", "env": settings.APP_ENV}
