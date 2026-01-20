"""
HABIBTI Backend API
Main FastAPI application
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core import settings, connect_to_mongo, close_mongo_connection, connect_to_redis, close_redis_connection
from app.core.rate_limit import init_app as init_rate_limiter
from app.core.logging import logger
from app.core.exceptions import http_exception_handler, validation_exception_handler, global_exception_handler
from app.api.v1 import api_router

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi import Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting HABIBTI API...")
    await connect_to_mongo()
    await connect_to_redis()
    
    # Initialize Rate Limiter
    init_rate_limiter(app)
    
    logger.info("HABIBTI API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HABIBTI API...")
    await close_mongo_connection()
    await close_redis_connection()
    logger.info("HABIBTI API shut down successfully")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME.upper(),
    description="Privacy-First End-to-End Encrypted Chat Application",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Exception Handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

from app.core.middleware import SecurityHeadersMiddleware

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and responses"""
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    logger.info(f"Response: {response.status_code}")
    return response

# Add Middleware
app.add_middleware(SecurityHeadersMiddleware)






# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.netlify\.app",  # Allow Netlify deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.APP_ENV
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
