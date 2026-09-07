import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.repositories.automation_repository import automation_repository
from app.repositories.automation_execution_repository import automation_execution_repository

logger = logging.getLogger(__name__)


class CommentTriggerService:
    """
    Comment Trigger Engine (Phase 3).
    Evaluates incoming Facebook and Instagram comments against ACTIVE automations
    and creates idempotent AutomationExecution records in PENDING status.
    STRICT BOUNDARY: Does NOT send public replies, Instagram DMs, or Facebook messages.
    """

    @staticmethod
    def normalize_keywords(raw_keywords: List[str]) -> List[str]:
        """Normalize keyword list: lowercase, strip whitespace, remove empty values, deduplicate."""
        seen = set()
        normalized = []
        for kw in raw_keywords:
            if not isinstance(kw, str):
                continue
            cleaned = kw.strip().lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)
        return normalized

    @staticmethod
    def match_keyword(comment_text: Optional[str], keywords: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Evaluate keywords against comment text using word/phrase boundary matching.
        Case-insensitive and ignores surrounding punctuation.
        Avoids false-positive substring matches (e.g. 'price' will NOT match 'surprise').
        Returns (is_match, matched_keyword).
        """
        if not comment_text or not keywords:
            return False, None

        cleaned_text = comment_text.strip().lower()
        if not cleaned_text:
            return False, None

        for kw in keywords:
            cleaned_kw = kw.strip().lower()
            if not cleaned_kw:
                continue

            # Word boundary regex matching for words or phrases
            # e.g., r'(?:^|\W)price(?:$|\W)' or r'\bprice\b'
            pattern = r'\b' + re.escape(cleaned_kw) + r'\b'
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                return True, cleaned_kw

        return False, None

    def is_owner_comment(self, db: Session, comment: SocialComment, account: SocialAccount) -> bool:
        """
        Determine if the comment was authored by the page/account itself or is an echo of an owner reply.
        Returns True if owner-generated (should be ignored by trigger engine).
        """
        # 1. Echo of owner reply in SocialCommentReply
        if comment.external_comment_id:
            existing_reply = db.query(SocialCommentReply).filter(
                SocialCommentReply.user_id == account.user_id,
                SocialCommentReply.platform == account.platform,
                SocialCommentReply.external_reply_id == comment.external_comment_id
            ).first()
            if existing_reply:
                logger.info(
                    f"[COMMENT_TRIGGER] Comment {comment.external_comment_id} is an echo of owner reply #{existing_reply.id}. Skipping."
                )
                return True

        # 2. Match commenter ID against connected Page ID / Instagram Account ID
        if comment.commenter_id:
            # Facebook Page ID or Instagram Account ID
            if str(comment.commenter_id) == str(account.account_id):
                logger.info(
                    f"[COMMENT_TRIGGER] Comment {comment.external_comment_id} authored by account owner ID {account.account_id}. Skipping."
                )
                return True

            # If account has metadata with linked Instagram Business Account ID
            if isinstance(account.metadata_json, dict):
                ig_biz_id = account.metadata_json.get("instagram_business_account", {}).get("id")
                if ig_biz_id and str(comment.commenter_id) == str(ig_biz_id):
                    logger.info(
                        f"[COMMENT_TRIGGER] Comment {comment.external_comment_id} authored by IG business ID {ig_biz_id}. Skipping."
                    )
                    return True

        # 3. Match commenter username against account username/name if commenter_id was absent
        if comment.commenter_name and account.account_name:
            if comment.commenter_name.strip().lower() == account.account_name.strip().lower():
                # For Facebook Page matching
                if not comment.commenter_id or str(comment.commenter_id) == str(account.account_id):
                    logger.info(
                        f"[COMMENT_TRIGGER] Comment {comment.external_comment_id} authored by owner name '{account.account_name}'. Skipping."
                    )
                    return True

        return False

    def find_candidate_automations(
        self,
        db: Session,
        account: SocialAccount,
        external_post_id: Optional[str]
    ) -> List[Automation]:
        """
        Query candidate ACTIVE automations for the social account and post.
        Uses database index on (social_account_id, external_post_id, status).
        """
        if not external_post_id:
            return []

        # Find active automations belonging to this account and platform
        query = db.query(Automation).filter(
            Automation.social_account_id == account.id,
            Automation.user_id == account.user_id,
            Automation.platform == account.platform,
            Automation.status == AutomationStatus.ACTIVE.value,
            Automation.post_target_type == PostTargetType.SPECIFIC_POST.value,
        )

        candidates = query.all()
        matched_automations = []

        for auto in candidates:
            # Match post ID: exact match or Facebook page_post suffix match
            auto_post_id = str(auto.external_post_id) if auto.external_post_id else None
            incoming_post_id = str(external_post_id)

            if not auto_post_id:
                continue

            if (
                auto_post_id == incoming_post_id or
                incoming_post_id.endswith(f"_{auto_post_id}") or
                auto_post_id.endswith(f"_{incoming_post_id}")
            ):
                matched_automations.append(auto)

        return matched_automations

    def evaluate_trigger(
        self,
        automation: Automation,
        comment: SocialComment
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if comment triggers this specific automation.
        Returns (is_matched, matched_keyword).
        """
        if automation.trigger_type == TriggerType.ANY_COMMENT.value:
            return True, None

        if automation.trigger_type == TriggerType.KEYWORD.value:
            raw_keywords = automation.trigger_config.get("keywords", []) if isinstance(automation.trigger_config, dict) else []
            normalized_kws = self.normalize_keywords(raw_keywords)
            return self.match_keyword(comment.comment_text, normalized_kws)

        return False, None

    def create_execution_idempotent(
        self,
        db: Session,
        automation: Automation,
        comment: SocialComment,
        matched_keyword: Optional[str] = None
    ) -> Optional[AutomationExecution]:
        """
        Idempotently create an AutomationExecution record in PENDING status.
        Handles concurrent race conditions using the unique constraint on (automation_id, external_comment_id).
        """
        if not comment.external_comment_id:
            logger.warning(f"[COMMENT_TRIGGER] Comment #{comment.id} missing external_comment_id. Cannot create execution.")
            return None

        # 1. Check if execution already exists
        existing = automation_execution_repository.get_by_automation_and_comment(
            db=db,
            automation_id=automation.id,
            external_comment_id=comment.external_comment_id
        )
        if existing:
            logger.info(
                f"[COMMENT_TRIGGER] Idempotent hit: Execution #{existing.id} already exists for automation #{automation.id} and comment {comment.external_comment_id}."
            )
            return existing

        # 2. Determine initial action status flags
        action_cfg = automation.action_config or {}
        pub_enabled = bool(action_cfg.get("public_reply", {}).get("enabled", False))
        priv_enabled = bool(action_cfg.get("private_message", {}).get("enabled", False))

        # 3. Create new PENDING execution record
        new_execution = AutomationExecution(
            automation_id=automation.id,
            user_id=automation.user_id,
            social_account_id=automation.social_account_id,
            comment_id=comment.id,
            external_comment_id=comment.external_comment_id,
            external_post_id=comment.external_post_id,
            platform=automation.platform,
            contact_identifier=comment.commenter_id,
            contact_name=comment.commenter_name,
            status=ExecutionStatus.PENDING.value,
            trigger_result={
                "matched": True,
                "trigger_type": automation.trigger_type,
                "matched_keyword": matched_keyword,
                "comment_text": comment.comment_text,
            },
            public_reply_status=ActionExecutionStatus.PENDING.value if pub_enabled else ActionExecutionStatus.SKIPPED.value,
            public_reply_result=None,
            private_message_status=ActionExecutionStatus.PENDING.value if priv_enabled else ActionExecutionStatus.SKIPPED.value,
            private_message_result=None,
        )

        try:
            db.add(new_execution)
            db.commit()
            db.refresh(new_execution)
            logger.info(
                f"[COMMENT_TRIGGER] Created AutomationExecution #{new_execution.id} (status=PENDING) for automation '{automation.name}' (ID #{automation.id}) and comment {comment.external_comment_id}."
            )
            return new_execution
        except IntegrityError:
            db.rollback()
            # Concurrent duplicate conflict caught safely
            existing_after_race = automation_execution_repository.get_by_automation_and_comment(
                db=db,
                automation_id=automation.id,
                external_comment_id=comment.external_comment_id
            )
            if existing_after_race:
                logger.info(
                    f"[COMMENT_TRIGGER] Concurrent race safely resolved: Execution #{existing_after_race.id} found for automation #{automation.id} and comment {comment.external_comment_id}."
                )
                return existing_after_race
            logger.error(
                f"[COMMENT_TRIGGER] IntegrityError inserting execution for automation #{automation.id} and comment {comment.external_comment_id}, but record not found."
            )
            return None

    def evaluate_comment(
        self,
        db: Session,
        comment: SocialComment,
        account: SocialAccount
    ) -> List[AutomationExecution]:
        """
        Main entrypoint for Comment Trigger Engine.
        Evaluates a newly received/ingested comment against candidate active automations.
        """
        if not comment or not account:
            return []

        # 1. Owner comment protection
        if self.is_owner_comment(db, comment, account):
            logger.info(
                f"[COMMENT_TRIGGER] Comment {comment.external_comment_id} on {account.platform} account #{account.id} is an owner comment. Ignoring."
            )
            return []

        # 2. Find candidate active automations targeting this post
        candidates = self.find_candidate_automations(
            db=db,
            account=account,
            external_post_id=comment.external_post_id
        )

        if not candidates:
            return []

        executions: List[AutomationExecution] = []

        # 3. Evaluate each candidate automation
        for auto in candidates:
            is_matched, matched_kw = self.evaluate_trigger(auto, comment)
            if is_matched:
                logger.info(
                    f"[COMMENT_TRIGGER] MATCH: Automation '{auto.name}' (ID #{auto.id}, trigger={auto.trigger_type}) matched comment {comment.external_comment_id}."
                )
                exec_record = self.create_execution_idempotent(
                    db=db,
                    automation=auto,
                    comment=comment,
                    matched_keyword=matched_kw
                )
                if exec_record:
                    executions.append(exec_record)
            else:
                logger.debug(
                    f"[COMMENT_TRIGGER] NO_MATCH: Automation '{auto.name}' (ID #{auto.id}) did not match comment {comment.external_comment_id}."
                )

        return executions


comment_trigger_service = CommentTriggerService()
