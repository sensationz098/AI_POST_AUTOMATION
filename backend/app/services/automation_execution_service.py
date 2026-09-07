import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.automation import Automation, AutomationStatus
from app.models.automation_execution import AutomationExecution, ExecutionStatus, ActionExecutionStatus
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.core.database import SessionLocal
from app.core.security_encryption import decrypt_token
from app.services.meta_service import meta_service, MetaPublishException, is_ambiguous_meta_error

logger = logging.getLogger(__name__)

# Dedicated thread pool for async execution without blocking webhook response
_execution_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="auto_exec_worker")


def utc_now():
    return datetime.now(timezone.utc)


class AutomationExecutionService:
    """
    Phase 4: Automation Execution Engine.
    Processes PENDING AutomationExecution records, performing public comment replies
    and private messages with independent partial failure handling and thread-safe claiming.
    STRICT BOUNDARY: Uses exact configured template text (NO AI / RAG).
    """

    @staticmethod
    def determine_retryability(exc: Exception) -> bool:
        """
        Evaluate whether an API exception represents a transient/retryable condition
        (e.g., HTTP 429 rate limit, 5xx server error, connection timeout) vs permanent failure.
        """
        if isinstance(exc, MetaPublishException):
            code = exc.status_code
            if code in (429, 500, 502, 503, 504):
                return True
            err_msg = (exc.error_message or "").lower()
            if "rate" in err_msg or "limit" in err_msg or "timeout" in err_msg or "timed out" in err_msg:
                return True
            return False

        err_str = str(exc).lower()
        if "timeout" in err_str or "timed out" in err_str or "connection" in err_str or "429" in err_str:
            return True
        return False

    def claim_execution(self, db: Session, execution_id: int) -> Optional[AutomationExecution]:
        """
        Atomically claim a PENDING or retryable execution record for processing.
        Prevents concurrent processing across multiple workers.
        Returns the claimed AutomationExecution in RUNNING status, or None if already claimed.
        """
        try:
            # Query candidate execution
            execution = db.query(AutomationExecution).filter(
                AutomationExecution.id == execution_id,
                or_(
                    AutomationExecution.status == ExecutionStatus.PENDING.value,
                    AutomationExecution.status == ExecutionStatus.PARTIAL_FAILURE.value,
                    AutomationExecution.status == ExecutionStatus.FAILED.value,
                )
            ).with_for_update().first()

            if not execution:
                logger.info(
                    f"[AUTOMATION_EXECUTION] Execution #{execution_id} cannot be claimed (not in PENDING/retryable state)."
                )
                return None

            execution.status = ExecutionStatus.RUNNING.value
            execution.updated_at = utc_now()
            db.commit()
            db.refresh(execution)

            logger.info(f"[AUTOMATION_EXECUTION] Claiming execution {execution.id}")
            logger.info(
                f"[AUTOMATION_EXECUTION] automation_id={execution.automation_id} platform={execution.platform}"
            )
            return execution
        except Exception as e:
            db.rollback()
            logger.error(f"[AUTOMATION_EXECUTION] Error claiming execution #{execution_id}: {e}")
            return None

    def execute_public_reply(
        self,
        db: Session,
        execution: AutomationExecution,
        automation: Automation,
        account: SocialAccount,
        comment: Optional[SocialComment],
        decrypted_token: str
    ) -> bool:
        """
        Execute configured public comment reply on the triggering comment.
        Persists action-level success immediately.
        """
        action_cfg = automation.action_config or {}
        pub_cfg = action_cfg.get("public_reply", {})
        if not pub_cfg.get("enabled", False):
            execution.public_reply_status = ActionExecutionStatus.SKIPPED.value
            db.commit()
            return True

        # If already succeeded in a prior partial run, do not resend
        if execution.public_reply_status == ActionExecutionStatus.SUCCESS.value:
            logger.info(
                f"[AUTOMATION_EXECUTION] Public reply for execution #{execution.id} already SUCCESS. Skipping resend."
            )
            return True

        variations = pub_cfg.get("variations", [])
        if not variations:
            execution.public_reply_status = ActionExecutionStatus.FAILED.value
            execution.public_reply_result = {"status": "FAILED", "error": "No reply variations configured."}
            db.commit()
            return False

        # Deterministic variation selection based on execution ID
        reply_text = variations[execution.id % len(variations)]

        logger.info("[AUTOMATION_EXECUTION] public_reply=STARTED")
        try:
            target_comment_id = execution.external_comment_id
            if execution.platform == "facebook":
                res = meta_service.reply_to_facebook_comment(
                    comment_id=target_comment_id,
                    access_token=decrypted_token,
                    message=reply_text
                )
            elif execution.platform == "instagram":
                res = meta_service.reply_to_instagram_comment(
                    comment_id=target_comment_id,
                    access_token=decrypted_token,
                    message=reply_text
                )
            else:
                raise MetaPublishException(f"Unsupported platform '{execution.platform}' for public reply.")

            reply_id = res.get("id") or res.get("external_reply_id")

            # Persist action success immediately
            execution.public_reply_status = ActionExecutionStatus.SUCCESS.value
            execution.public_reply_result = {
                "status": "SUCCESS",
                "external_reply_id": reply_id,
                "message": reply_text
            }
            db.commit()

            # Record in SocialCommentReply for audit and owner echo prevention if comment_id is present
            if execution.comment_id:
                try:
                    reply_audit = SocialCommentReply(
                        comment_id=execution.comment_id,
                        user_id=execution.user_id,
                        platform=execution.platform,
                        external_reply_id=str(reply_id) if reply_id else None,
                        message=reply_text,
                        status="SUCCESS"
                    )
                    db.add(reply_audit)
                    db.commit()
                except Exception as audit_err:
                    db.rollback()
                    logger.warning(f"[AUTOMATION_EXECUTION] Could not record SocialCommentReply audit row: {audit_err}")

            logger.info("[AUTOMATION_EXECUTION] public_reply=SENT")
            return True
        except Exception as err:
            retryable = self.determine_retryability(err)
            execution.public_reply_status = ActionExecutionStatus.FAILED.value
            execution.public_reply_result = {
                "status": "FAILED",
                "error": str(err),
                "retryable": retryable
            }
            db.commit()
            logger.error(
                f"[AUTOMATION_EXECUTION] action=public_reply FAILED retryable={str(retryable).lower()} | error={err}"
            )
            return False

    def execute_private_message(
        self,
        db: Session,
        execution: AutomationExecution,
        automation: Automation,
        account: SocialAccount,
        comment: Optional[SocialComment],
        decrypted_token: str
    ) -> bool:
        """
        Execute configured private message to the user who triggered the comment.
        Persists action-level success immediately.
        """
        action_cfg = automation.action_config or {}
        priv_cfg = action_cfg.get("private_message", {})
        if not priv_cfg.get("enabled", False):
            execution.private_message_status = ActionExecutionStatus.SKIPPED.value
            db.commit()
            return True

        # If already succeeded in a prior partial run, do not resend
        if execution.private_message_status == ActionExecutionStatus.SUCCESS.value:
            logger.info(
                f"[AUTOMATION_EXECUTION] Private message for execution #{execution.id} already SUCCESS. Skipping resend."
            )
            return True

        msg_text = priv_cfg.get("message")
        if not msg_text or not msg_text.strip():
            execution.private_message_status = ActionExecutionStatus.FAILED.value
            execution.private_message_result = {"status": "FAILED", "error": "No private message text configured."}
            db.commit()
            return False

        msg_text = msg_text.strip()
        recipient_id = execution.contact_identifier
        comment_id = execution.external_comment_id

        logger.info("[AUTOMATION_EXECUTION] private_message=STARTED")
        try:
            if execution.platform == "facebook":
                res = meta_service.send_facebook_private_message(
                    recipient_id=recipient_id,
                    access_token=decrypted_token,
                    message=msg_text,
                    comment_id=comment_id
                )
            elif execution.platform == "instagram":
                res = meta_service.send_instagram_private_message(
                    recipient_id=recipient_id,
                    access_token=decrypted_token,
                    message=msg_text,
                    comment_id=comment_id
                )
            else:
                raise MetaPublishException(f"Unsupported platform '{execution.platform}' for private message.")

            msg_id = res.get("message_id") or res.get("id")

            # Persist action success immediately
            execution.private_message_status = ActionExecutionStatus.SUCCESS.value
            execution.private_message_result = {
                "status": "SUCCESS",
                "external_message_id": msg_id,
                "message": msg_text
            }
            db.commit()

            logger.info("[AUTOMATION_EXECUTION] private_message=SENT")
            return True
        except Exception as err:
            retryable = self.determine_retryability(err)
            execution.private_message_status = ActionExecutionStatus.FAILED.value
            execution.private_message_result = {
                "status": "FAILED",
                "error": str(err),
                "retryable": retryable
            }
            db.commit()
            logger.error(
                f"[AUTOMATION_EXECUTION] action=private_message FAILED retryable={str(retryable).lower()} | error={err}"
            )
            return False

    def execute_pending_execution(
        self,
        execution_id: int,
        db: Optional[Session] = None
    ) -> Optional[AutomationExecution]:
        """
        Main execution workflow for an AutomationExecution record:
        1. Claim execution atomically.
        2. Validate execution context, automation status, and social account.
        3. Execute public reply and private message independently.
        4. Finalize status (COMPLETED, FAILED, or PARTIAL_FAILURE).
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True

        try:
            execution = self.claim_execution(db, execution_id)
            if not execution:
                return None

            # Load automation
            automation = db.query(Automation).filter(Automation.id == execution.automation_id).first()
            if not automation:
                execution.status = ExecutionStatus.FAILED.value
                execution.error_message = "Automation record not found or deleted."
                db.commit()
                logger.error(f"[AUTOMATION_EXECUTION] execution_id={execution.id} status=FAILED error=Automation not found")
                return execution

            # Guardrail: Automation must be ACTIVE at the time of execution
            if automation.status != AutomationStatus.ACTIVE.value:
                execution.status = ExecutionStatus.FAILED.value
                execution.error_message = f"Automation #{automation.id} is in status '{automation.status}'. Must be ACTIVE to execute."
                db.commit()
                logger.warning(
                    f"[AUTOMATION_EXECUTION] execution_id={execution.id} status=FAILED error=Automation is {automation.status}"
                )
                return execution

            # Load social account
            account = db.query(SocialAccount).filter(SocialAccount.id == execution.social_account_id).first()
            if not account or account.status != "CONNECTED":
                execution.status = ExecutionStatus.FAILED.value
                execution.error_message = "Social account not found or disconnected."
                db.commit()
                logger.error(f"[AUTOMATION_EXECUTION] execution_id={execution.id} status=FAILED error=Account not connected")
                return execution

            # Load social comment
            comment = db.query(SocialComment).filter(SocialComment.id == execution.comment_id).first() if execution.comment_id else None

            # Decrypt access token safely
            decrypted_token = decrypt_token(account.access_token) or account.access_token
            if not decrypted_token:
                execution.status = ExecutionStatus.FAILED.value
                execution.error_message = "Could not decrypt social account access token."
                db.commit()
                return execution

            # Execute enabled actions independently
            pub_ok = self.execute_public_reply(
                db=db,
                execution=execution,
                automation=automation,
                account=account,
                comment=comment,
                decrypted_token=decrypted_token
            )

            priv_ok = self.execute_private_message(
                db=db,
                execution=execution,
                automation=automation,
                account=account,
                comment=comment,
                decrypted_token=decrypted_token
            )

            # Finalize overall execution status
            pub_status = execution.public_reply_status
            priv_status = execution.private_message_status

            all_succeeded_or_skipped = (
                pub_status in (ActionExecutionStatus.SUCCESS.value, ActionExecutionStatus.SKIPPED.value) and
                priv_status in (ActionExecutionStatus.SUCCESS.value, ActionExecutionStatus.SKIPPED.value)
            )
            all_failed = (
                (pub_status == ActionExecutionStatus.FAILED.value or pub_status == ActionExecutionStatus.SKIPPED.value) and
                (priv_status == ActionExecutionStatus.FAILED.value or priv_status == ActionExecutionStatus.SKIPPED.value) and
                not (pub_status == ActionExecutionStatus.SKIPPED.value and priv_status == ActionExecutionStatus.SKIPPED.value)
            )

            if all_succeeded_or_skipped:
                execution.status = ExecutionStatus.COMPLETED.value
                execution.error_message = None
            elif pub_status == ActionExecutionStatus.SUCCESS.value or priv_status == ActionExecutionStatus.SUCCESS.value:
                execution.status = ExecutionStatus.PARTIAL_FAILURE.value
            else:
                execution.status = ExecutionStatus.FAILED.value

            execution.updated_at = utc_now()
            db.commit()
            db.refresh(execution)

            logger.info(f"[AUTOMATION_EXECUTION] execution_id={execution.id} status={execution.status}")
            return execution
        except Exception as top_err:
            if db:
                db.rollback()
            logger.error(f"[AUTOMATION_EXECUTION] Unexpected error executing execution #{execution_id}: {top_err}")
            return None
        finally:
            if should_close and db:
                db.close()

    def dispatch_async(self, execution_id: int):
        """Enqueue an execution ID for non-blocking asynchronous processing."""
        _execution_executor.submit(self.execute_pending_execution, execution_id)

    def process_pending_executions(self, db: Session, limit: int = 50) -> List[AutomationExecution]:
        """Process batch of pending/retryable executions (useful for worker/scheduler polling)."""
        pending_records = db.query(AutomationExecution).filter(
            AutomationExecution.status.in_([
                ExecutionStatus.PENDING.value,
                ExecutionStatus.PARTIAL_FAILURE.value
            ])
        ).order_by(AutomationExecution.created_at.asc()).limit(limit).all()
        pending_ids = [rec.id for rec in pending_records]

        results = []
        for exec_id in pending_ids:
            res = self.execute_pending_execution(exec_id, db=db)
            if res:
                results.append(res)
        return results


automation_execution_service = AutomationExecutionService()
