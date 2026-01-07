import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .database import init_db, close_db
from .routers import (
    auth_router,
    users_router,
    search_router,
    downloads_router,
    playlists_router,
    stream_router
)
from .services.telegram_client import telegram_service
from .services.download_queue import download_queue

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Spotizer API...")
    await init_db()
    logger.info("Database initialized")
    await telegram_service.start()
    logger.info("Telegram service started")
    await download_queue.start()
    logger.info("Download queue worker started")
    yield
    # Shutdown
    logger.info("Shutting down Spotizer API...")
    await download_queue.stop()
    logger.info("Download queue worker stopped")
    await telegram_service.stop()
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Spotizer API",
    description="""
    Spotizer API - Backend for Spotizer Music Downloader Bot

    ## Features
    * User authentication and management
    * Search music on Spotify
    * Download tracks, albums, and playlists
    * Create and manage personal playlists
    * Download history tracking

    ## Authentication
    Most endpoints require authentication. Use the `/auth/login` endpoint to get a JWT token.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(search_router, prefix=settings.API_V1_PREFIX)
app.include_router(downloads_router, prefix=settings.API_V1_PREFIX)
app.include_router(playlists_router, prefix=settings.API_V1_PREFIX)
app.include_router(stream_router, prefix=settings.API_V1_PREFIX)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Spotizer API",
        "docs": "/docs",
        "version": "1.0.0"
    }


# Convenience routes for frontend compatibility
from fastapi import Query
from fastapi.responses import RedirectResponse

@app.get(f"{settings.API_V1_PREFIX}/settings", tags=["Settings"])
async def get_settings_redirect(request: Request):
    """Redirect to user settings endpoint"""
    return RedirectResponse(url=f"{settings.API_V1_PREFIX}/users/me/settings", status_code=307)


@app.patch(f"{settings.API_V1_PREFIX}/settings", tags=["Settings"])
@app.put(f"{settings.API_V1_PREFIX}/settings", tags=["Settings"])
async def update_settings_redirect(request: Request):
    """Redirect to user settings update endpoint"""
    return RedirectResponse(url=f"{settings.API_V1_PREFIX}/users/me/settings", status_code=307)


@app.get(f"{settings.API_V1_PREFIX}/history", tags=["History"])
async def get_history_redirect(
    request: Request,
    limit: int = Query(20, ge=1, le=100)
):
    """Redirect to downloads history endpoint"""
    return RedirectResponse(url=f"{settings.API_V1_PREFIX}/downloads/history?page_size={limit}", status_code=307)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
