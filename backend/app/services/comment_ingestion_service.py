import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.repositories.social_account_repository import social_account_repo
from app.repositories.social_comment_repository import social_comment_repo
from app.models.social_comment import SocialComment

logger = logging.getLogger(__name__)

class MetaCommentIngestionService:
    def parse_and_ingest_payload(self, db: Session, payload: Dict[str, Any]) -> List[SocialComment]:
        """
        Safely parse incoming Meta Webhook payload for Facebook & Instagram comment events and store them.
        Strictly enforces account identification, user isolation, and event deduplication.
        Does NOT raise exceptions to ensure webhook HTTP 200 responses.
        NEVER logs tokens, secrets, or sensitive user payload data.
        """
        if not isinstance(payload, dict):
            return []

        webhook_object = payload.get("object", "")
        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return []

        ingested_comments: List[SocialComment] = []

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            entry_id = str(entry.get("id", ""))
            changes = entry.get("changes", [])
            if not entry_id or not isinstance(changes, list):
                continue

            if webhook_object == "page":
                comments = self._process_facebook_page_changes(db, entry_id, changes, webhook_object)
                ingested_comments.extend(comments)
            elif webhook_object == "instagram":
                comments = self._process_instagram_changes(db, entry_id, changes, webhook_object)
                ingested_comments.extend(comments)

        return ingested_comments

    def _process_facebook_page_changes(
        self,
        db: Session,
        page_id: str,
        changes: List[Any],
        webhook_object: str
    ) -> List[SocialComment]:
        """Parse Facebook Page 'feed' changes for comment events."""
        account = social_account_repo.get_by_account_id(db, user_id=None, platform="facebook", account_id=page_id)
        if not account:
            logger.info(f"[META_WEBHOOK_INGEST] Facebook Page {page_id} not found in connected social accounts. Ignoring event.")
            return []

        created_comments = []
        for change in changes:
            if not isinstance(change, dict):
                continue

            field = change.get("field")
            value = change.get("value", {})
            if field != "feed" or not isinstance(value, dict):
                continue

            # Check if this change represents a comment event
            item = value.get("item")
            verb = value.get("verb", "add")
            comment_id = value.get("comment_id")

            # Must be a comment item or explicit comment_id with add verb
            if item != "comment" and not comment_id:
                continue
            if verb not in ("add", "edited", None):
                # Ignore deletions or non-add/edit actions for ingestion
                continue

            # Extract fields safely
            comment_id = str(comment_id or value.get("id", ""))
            if not comment_id:
                continue

            post_id = value.get("post_id") or value.get("parent_id")
            parent_id = value.get("parent_id") if value.get("parent_id") != post_id else None
            comment_text = value.get("message")
            sender = value.get("from", {}) if isinstance(value.get("from"), dict) else {}
            commenter_id = str(sender.get("id", "")) if sender.get("id") else None
            commenter_name = sender.get("name")

            raw_time = value.get("created_time")
            event_ts = None
            if raw_time:
                try:
                    event_ts = datetime.fromtimestamp(int(raw_time), tz=timezone.utc)
                except (ValueError, TypeError):
                    event_ts = datetime.now(timezone.utc)

            comment = social_comment_repo.create_or_get_existing(
                db=db,
                user_id=account.user_id,
                social_account_id=account.id,
                platform="facebook",
                external_comment_id=comment_id,
                external_post_id=str(post_id) if post_id else None,
                parent_comment_id=str(parent_id) if parent_id else None,
                comment_text=comment_text,
                commenter_id=commenter_id,
                commenter_name=commenter_name,
                event_timestamp=event_ts,
                webhook_object=webhook_object,
                processing_status="RECEIVED",
                metadata_json={"item": item, "verb": verb}
            )
            created_comments.append(comment)

        return created_comments

    def _process_instagram_changes(
        self,
        db: Session,
        ig_account_id: str,
        changes: List[Any],
        webhook_object: str
    ) -> List[SocialComment]:
        """Parse Instagram account 'comments' or 'mentions' changes."""
        account = social_account_repo.get_by_account_id(db, user_id=None, platform="instagram", account_id=ig_account_id)
        if not account:
            logger.info(f"[META_WEBHOOK_INGEST] Instagram Account {ig_account_id} not found in connected social accounts. Ignoring event.")
            return []

        created_comments = []
        for change in changes:
            if not isinstance(change, dict):
                continue

            field = change.get("field")
            value = change.get("value", {})
            if field not in ("comments", "mentions") or not isinstance(value, dict):
                continue

            comment_id = str(value.get("id", ""))
            if not comment_id:
                continue

            media = value.get("media", {}) if isinstance(value.get("media"), dict) else {}
            media_id = media.get("id") or value.get("media_id")
            comment_text = value.get("text")
            parent_id = value.get("parent_id")
            
            sender = value.get("from", {}) if isinstance(value.get("from"), dict) else {}
            commenter_id = str(sender.get("id", "")) if sender.get("id") else None
            commenter_name = sender.get("username") or sender.get("name")

            raw_time = value.get("created_time")
            event_ts = None
            if raw_time:
                try:
                    event_ts = datetime.fromtimestamp(int(raw_time), tz=timezone.utc)
                except (ValueError, TypeError):
                    event_ts = datetime.now(timezone.utc)

            comment = social_comment_repo.create_or_get_existing(
                db=db,
                user_id=account.user_id,
                social_account_id=account.id,
                platform="instagram",
                external_comment_id=comment_id,
                external_post_id=str(media_id) if media_id else None,
                parent_comment_id=str(parent_id) if parent_id else None,
                comment_text=comment_text,
                commenter_id=commenter_id,
                commenter_name=commenter_name,
                event_timestamp=event_ts,
                webhook_object=webhook_object,
                processing_status="RECEIVED",
                metadata_json={"field": field}
            )
            created_comments.append(comment)

        return created_comments

meta_comment_ingestion_service = MetaCommentIngestionService()
