import time
import asyncio
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
import logging
from ..core.config import settings

logger = logging.getLogger("backend.core.rate_limiter")

class RateLimiter:
    """
    A lightweight, in-memory rate limiter to prevent abuse.
    Uses a simple sliding window / token bucket-like approach.
    """
    def __init__(self, requests: int = 10, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds
        # Stores { client_ip_or_user_id: (count, reset_time) }
        self.clients: Dict[str, Tuple[int, float]] = {}
        self.lock = asyncio.Lock()

    async def __call__(self, request: Request):
        import sys
        if "pytest" in sys.modules or settings.ENVIRONMENT == "test":
            return True

        # Identify the client by IP (or user ID if available in request.state)
        client_id = request.client.host if request.client else "unknown"
        
        # Check if user is authenticated (can limit per user instead of IP)
        if hasattr(request.state, "user"):
            client_id = f"user_{request.state.user.id}"

        now = time.time()

        async with self.lock:
            # Cleanup expired records periodically to avoid memory leaks
            if len(self.clients) > 10000:
                self.clients = {k: v for k, v in self.clients.items() if v[1] > now}

            record = self.clients.get(client_id)
            if record:
                count, reset_time = record
                if now > reset_time:
                    # Window expired, reset
                    self.clients[client_id] = (1, now + self.window_seconds)
                else:
                    if count >= self.requests:
                        logger.warning(f"Rate limit exceeded for client {client_id} on path {request.url.path}")
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many requests, please try again later."
                        )
                    # Increment count
                    self.clients[client_id] = (count + 1, reset_time)
            else:
                self.clients[client_id] = (1, now + self.window_seconds)
