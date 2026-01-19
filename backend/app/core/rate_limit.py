"""
Rate limiting configuration using SlowAPI
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.callback import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Global limiter instance
# Uses remote address (IP) as the key
limiter = Limiter(key_func=get_remote_address)

def init_app(app):
    """Initialize rate limiter with FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
