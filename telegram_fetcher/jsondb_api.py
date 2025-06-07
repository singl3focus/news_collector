from fastapi import HTTPException
from pydantic import BaseModel
from jsondb import JsonDB
import time
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 100  # requests per window

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}

    def is_rate_limited(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests
        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < RATE_LIMIT_WINDOW]
        
        if len(self.requests[client_id]) >= RATE_LIMIT_MAX_REQUESTS:
            return True
            
        self.requests[client_id].append(now)
        return False

rate_limiter = RateLimiter()
db = JsonDB()

class ChannelIn(BaseModel):
    link: str
    title: str = "" 