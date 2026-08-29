import json
import hmac
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Query, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.services.comment_ingestion_service import meta_comment_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Meta Webhooks"])

def verify_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Validate incoming Meta X-Hub-Signature-256 HMAC payload using META_APP_SECRET."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    if not settings.META_APP_SECRET:
        return False

    expected_hash = hmac.new(
        settings.META_APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    expected_signature = f"sha256={expected_hash}"

    return hmac.compare_digest(expected_signature, signature_header)

@router.get("/meta", response_class=Response)
def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge")
):
    """
    Meta Webhook Verification Endpoint (GET /api/v1/webhooks/meta).
    Verifies subscription challenge sent by Meta Graph API.
    Returns plain text challenge string upon successful verification.
    Does NOT require JWT authentication.
    """
    expected_token = settings.META_WEBHOOK_VERIFY_TOKEN

    if not expected_token:
        logger.warning("[META_WEBHOOK] META_WEBHOOK_VERIFY_TOKEN is not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Webhook verify token is not configured on server."
        )

    if hub_mode == "subscribe" and hub_verify_token and hmac.compare_digest(hub_verify_token, expected_token):
        if hub_challenge:
            logger.info("[META_WEBHOOK] Meta webhook challenge verified successfully.")
            return Response(content=str(hub_challenge), media_type="text/plain", status_code=200)

    logger.warning("[META_WEBHOOK] Meta webhook verification failed: invalid mode or verify token mismatch.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Webhook verification failed."
    )

@router.post("/meta", status_code=status.HTTP_200_OK)
async def receive_meta_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Meta Webhook Event Receiver Endpoint (POST /api/v1/webhooks/meta).
    Validates payload integrity using X-Hub-Signature-256.
    Does NOT require JWT authentication.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256")

    if not signature_header:
        logger.warning("[META_WEBHOOK] Missing X-Hub-Signature-256 header in webhook payload.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Missing X-Hub-Signature-256 header."
        )

    if not verify_signature(raw_body, signature_header):
        logger.warning("[META_WEBHOOK] Invalid X-Hub-Signature-256 HMAC signature verification failure.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid signature."
        )

    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        obj_type = payload.get("object", "unknown")
        entry_list = payload.get("entry", [])
        entry_count = len(entry_list) if isinstance(entry_list, list) else 0

        # Safely extract high-level event type without sensitive content
        event_types = []
        if isinstance(entry_list, list):
            for entry in entry_list:
                changes = entry.get("changes", [])
                if isinstance(changes, list):
                    for c in changes:
                        field_name = c.get("field")
                        if field_name and field_name not in event_types:
                            event_types.append(field_name)

        event_str = f", Event types: {', '.join(event_types)}" if event_types else ""

        if obj_type in ("page", "instagram"):
            logger.info(f"[META_WEBHOOK] Validated Meta {obj_type.upper()} webhook event. Entry count: {entry_count}{event_str}")
        else:
            logger.info(f"[META_WEBHOOK] Validated Meta webhook event with object type: {obj_type}. Entry count: {entry_count}{event_str}")

        # Ingest comment events safely into database
        ingested = meta_comment_ingestion_service.parse_and_ingest_payload(db, payload)
        if ingested:
            logger.info(f"[META_WEBHOOK] Ingested {len(ingested)} comment event(s) into database.")
    except Exception as e:
        logger.error(f"[META_WEBHOOK] Error parsing valid webhook JSON payload: {e}")

    return {"status": "success"}
