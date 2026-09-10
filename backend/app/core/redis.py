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
    redis_url = settings.get_redis_url()
    try:
        kwargs = {"decode_responses": True}
        if redis_url.startswith("rediss://"):
            kwargs["ssl_cert_reqs"] = None
        _redis_client = redis.Redis.from_url(redis_url, **kwargs)
        _redis_client.ping()
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis connection failed ({redis_url}): {e}. Fallback to in-memory state dictionary.")
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

_in_memory_upload_sessions = {}

def set_upload_session(upload_id: str, session_data: dict, ttl_seconds: int = 86400) -> None:
    """Store YouTube resumable upload session data with TTL (default 24h)."""
    r = get_redis_client()
    if r:
        try:
            r.setex(f"yt_upload:{upload_id}", ttl_seconds, json.dumps(session_data))
            return
        except Exception as e:
            logger.error(f"Redis set_upload_session error: {e}")
    
    _in_memory_upload_sessions[upload_id] = session_data

def get_upload_session(upload_id: str) -> Optional[dict]:
    """Retrieve YouTube resumable upload session data."""
    if not upload_id:
        return None
    r = get_redis_client()
    if r:
        try:
            raw = r.get(f"yt_upload:{upload_id}")
            if raw:
                return json.loads(raw)
            return None
        except Exception as e:
            logger.error(f"Redis get_upload_session error: {e}")
    
    return _in_memory_upload_sessions.get(upload_id)

def update_upload_session(upload_id: str, updates: dict, ttl_seconds: int = 86400) -> Optional[dict]:
    """Update fields in an existing YouTube upload session."""
    session = get_upload_session(upload_id)
    if not session:
        return None
    session.update(updates)
    set_upload_session(upload_id, session, ttl_seconds=ttl_seconds)
    return session

def delete_upload_session(upload_id: str) -> None:
    """Delete a YouTube upload session once completed or expired."""
    if not upload_id:
        return
    r = get_redis_client()
    if r:
        try:
            r.delete(f"yt_upload:{upload_id}")
        except Exception as e:
            logger.error(f"Redis delete_upload_session error: {e}")
    _in_memory_upload_sessions.pop(upload_id, None)

