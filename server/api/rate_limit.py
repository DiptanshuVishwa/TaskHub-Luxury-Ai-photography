import redis
import jwt
from functools import wraps
from flask import request
from config import Config
from api.utils import api_response

redis_client = None
if Config.REDIS_URL:
    try:
        redis_client = redis.Redis.from_url(Config.REDIS_URL)
        print("Successfully initialized Upstash Redis client for Rate Limiting.")
    except Exception as e:
        print(f"Warning: Failed to connect to Redis: {e}. Rate limiter running in bypass mode.")

def limit_requests(limit, period, key_prefix):
    """
    Decorator to rate limit endpoints using Redis.
    limit: Max requests allowed
    period: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if redis_client is None:
                return f(*args, **kwargs)
            
            # Identify user by ID (from JWT cookie) or fallback to IP Address
            identifier = request.remote_addr
            token = request.cookies.get('token')
            if token:
                try:
                    data = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
                    if 'sub' in data:
                        identifier = data['sub']
                except Exception:
                    pass
            
            key = f"ratelimit:{key_prefix}:{identifier}"
            
            try:
                current_hits = redis_client.get(key)
                if current_hits and int(current_hits) >= limit:
                    ttl = redis_client.ttl(key)
                    return api_response(
                        success=False,
                        message="Rate limit exceeded. Slow down your requests.",
                        error=f"Limit: {limit} requests per {period}s window. Retry in {ttl}s.",
                        status=429
                    )
                
                pipe = redis_client.pipeline()
                pipe.incr(key)
                if not current_hits:
                    pipe.expire(key, period)
                pipe.execute()
            except Exception as e:
                # Robustness principle: log and bypass rate limiter if Redis is offline/unreachable
                print(f"Rate Limiter Redis transaction error: {e}")
                
            return f(*args, **kwargs)
        return decorated
    return decorator

# Specific limits specified in the assignment
# 100 API requests / minute
def limit_api_rate():
    return limit_requests(limit=100, period=60, key_prefix="api_min")

# 10 AI generations / hour
def limit_ai_rate():
    return limit_requests(limit=10, period=3600, key_prefix="ai_hour")
