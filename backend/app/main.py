import os
from dotenv import load_dotenv

# Load environment variables FIRST - before any other imports that might depend on them
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_LOCAL_PATH = os.path.join(BACKEND_DIR, '.env.local')
DOTENV_ROOT_PATH = os.path.join(os.path.dirname(BACKEND_DIR), '.env')

# Try to load .env.local first (for local development), then fallback to .env
if os.path.exists(DOTENV_LOCAL_PATH):
    print(f"Loading local environment from: {DOTENV_LOCAL_PATH}")
    load_dotenv(DOTENV_LOCAL_PATH)
else:
    print(f"Loading environment from: {DOTENV_ROOT_PATH}")
    load_dotenv(DOTENV_ROOT_PATH)

# Now import everything else
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints.analysis import router as analysis_router
from app.api.endpoints.reports import router as reports_router
from app.db import create_tables
from app.core.logging_config import ensure_logging_initialized, get_logger
# Import error handlers for task 5.3
from app.core.error_handlers import (
    TimesheetAnalysisError,
    timesheet_analysis_error_handler,
    general_exception_handler
)

# Initialize logging as early as possible
ensure_logging_initialized()
logger = get_logger("main")

# Create database tables
create_tables()
logger.info("Database tables created/verified")

app = FastAPI(
    title="Time Sheet Magic API",
    description="Automated timesheet analysis and compliance checking system",
    version="1.0.0",
    debug=False  # Set to True in development for detailed error responses
)

# Add CORS middleware to allow requests from Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://shiftiq.us",  # New production domain
        "https://www.shiftiq.us",  # Include www subdomain
        "https://timesheet-magic.vercel.app",
        "https://*.vercel.app",  # Allow any Vercel preview deployments
        "http://localhost:3000",  # Local development
        "http://localhost:3001",  # Alternative local port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register global error handlers (task 5.3)
app.add_exception_handler(TimesheetAnalysisError, timesheet_analysis_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "service": "Time Sheet Magic API",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }

logger.info("Time Sheet Magic API started successfully")
logger.info("Registered endpoints: /api/analyze, /api/submit-lead, /api/reports/*")
logger.info("Global error handlers registered for standardized error responses") 