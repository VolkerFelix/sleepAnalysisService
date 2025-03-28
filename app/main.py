from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings


def create_application() -> FastAPI:
    application = FastAPI(
        title="Areum Sleep Analysis Service",
        description="Microservice for analyzing and recognizing sleep patterns from sensor data",
        version=settings.VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
    )

    # Set up CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    application.include_router(api_router, prefix="/api")

    @application.get("/health")
    def health_check():
        return {"status": "healthy", "service": "sleep-analysis"}

    return application


app = create_application()