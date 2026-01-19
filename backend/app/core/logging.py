"""
Logging configuration
"""
import logging
import sys
from app.core import settings

class EndpointFilter(logging.Filter):
    """
    Filter out health check endpoints from logs
    """
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1

def setup_logging():
    """Configure structured logging"""
    logger = logging.getLogger("habibti")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    
    # Remove existing handlers
    logger.handlers = []
    logger.addHandler(console_handler)
    
    # Filter health checks from access logs if using uvicorn
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
    
    return logger

# Global logger
logger = setup_logging()
