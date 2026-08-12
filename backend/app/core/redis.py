import logging
import json
from typing import Optional, Any
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Fallback to in-memory state dictionary.")
        _redis_client = None
        return None

_in_memory_states = {}

def set_oauth_state(state_token: str, user_id: int, ttl_seconds: int = 900) -> None:
    """Store CSRF OAuth state tied to user_id with strict TTL (15 mins)."""
    r = get_redis_client()
    if r:
        try:
            r.setex(f"oauth_state:{state_token}", ttl_seconds, json.dumps({"user_id": user_id}))
            return
        except Exception as e:
            logger.error(f"Redis set_oauth_state error: {e}")
    
    # Fallback to local dict
    _in_memory_states[state_token] = {"user_id": user_id}

def pop_oauth_state(state_token: str) -> Optional[int]:
    """Atomically retrieve and delete CSRF OAuth state token (one-time use)."""
    if not state_token:
        return None
    r = get_redis_client()
    if r:
        try:
            key = f"oauth_state:{state_token}"
            raw = r.get(key)
            if raw:
                r.delete(key)
                data = json.loads(raw)
                return data.get("user_id")
            return None
        except Exception as e:
            logger.error(f"Redis pop_oauth_state error: {e}")

    # Fallback to local dict
    data = _in_memory_states.pop(state_token, None)
    if data:
        return data.get("user_id")
    return None
