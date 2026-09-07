import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.automation import Automation, AutomationStatus, TriggerType, PostTargetType
from app.models.social_account import SocialAccount
from app.models.post import Post
from app.repositories.automation_repository import automation_repository
from app.schemas.automation import AutomationCreate, AutomationUpdate

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = {"facebook", "instagram"}


class AutomationService:
    """Service handling validation, lifecycle, and CRUD operations for comment automations."""

    def _validate_platform(self, platform: str) -> str:
        norm_platform = platform.strip().lower() if platform else ""
        if norm_platform not in SUPPORTED_PLATFORMS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported platform '{platform}'. Supported platforms are: {', '.join(sorted(SUPPORTED_PLATFORMS))}."
            )
        return norm_platform

    def _validate_social_account(
        self, db: Session, user_id: int, social_account_id: int, platform: str
    ) -> SocialAccount:
        account = db.query(SocialAccount).filter(
            SocialAccount.id == social_account_id,
            SocialAccount.user_id == user_id
        ).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Social account not found or access denied."
            )

        if account.platform.strip().lower() != platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Social account platform '{account.platform}' does not match automation platform '{platform}'."
            )
        return account

    def _validate_post_target(
        self,
        db: Session,
        user_id: int,
        platform: str,
        post_target_type: str,
        internal_post_id: Optional[int],
        external_post_id: Optional[str]
    ) -> Tuple[Optional[int], Optional[str]]:
        if post_target_type != PostTargetType.SPECIFIC_POST.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported post target type '{post_target_type}'. V1 supports ONLY 'SPECIFIC_POST'."
            )

        resolved_internal_id = internal_post_id
        resolved_external_id = external_post_id.strip() if external_post_id and str(external_post_id).strip() else None

        if resolved_internal_id is not None:
            post = db.query(Post).filter(
                Post.id == resolved_internal_id,
                Post.user_id == user_id
            ).first()
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target post not found or access denied."
                )

            # Validate platform compatibility
            post_platforms = [p.lower() for p in (post.platforms or [])]
            if platform == "instagram":
                if not post.ig_media_id and "instagram" not in post_platforms:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected post is not configured for Instagram."
                    )
                if not resolved_external_id and post.ig_media_id:
                    resolved_external_id = post.ig_media_id
                elif resolved_external_id and post.ig_media_id and resolved_external_id != post.ig_media_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Specified external_post_id does not match post's Instagram media ID."
                    )
            elif platform == "facebook":
                if not post.fb_post_id and "facebook" not in post_platforms:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Selected post is not configured for Facebook."
                    )
                if not resolved_external_id and post.fb_post_id:
                    resolved_external_id = post.fb_post_id
                elif resolved_external_id and post.fb_post_id and resolved_external_id != post.fb_post_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Specified external_post_id does not match post's Facebook post ID."
                    )

            if not resolved_external_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Selected local post #{resolved_internal_id} has not been published to {platform} or lacks an external platform post ID."
                )

        elif resolved_external_id:
            # Check if there is an optional known internal post for this external ID
            if platform == "instagram":
                matched_post = db.query(Post).filter(Post.user_id == user_id, Post.ig_media_id == resolved_external_id).first()
            else:
                matched_post = db.query(Post).filter(Post.user_id == user_id, Post.fb_post_id == resolved_external_id).first()
            if matched_post:
                resolved_internal_id = matched_post.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A target post (external_post_id or published internal_post_id) must be specified for SPECIFIC_POST automations."
            )

        if not resolved_external_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid external platform post ID is required."
            )

        return resolved_internal_id, resolved_external_id

    def _validate_and_normalize_trigger(
        self, trigger_type: str, trigger_config: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        norm_trigger_type = trigger_type.strip().upper() if trigger_type else ""
        if norm_trigger_type not in {TriggerType.ANY_COMMENT.value, TriggerType.KEYWORD.value}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trigger type '{trigger_type}'. Supported: 'ANY_COMMENT', 'KEYWORD'."
            )

        if norm_trigger_type == TriggerType.ANY_COMMENT.value:
            return norm_trigger_type, {}

        # KEYWORD trigger validation
        cfg = trigger_config or {}
        raw_keywords = cfg.get("keywords")
        if not isinstance(raw_keywords, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Keyword trigger configuration must include a 'keywords' list."
            )

        normalized_keywords = []
        for kw in raw_keywords:
            if isinstance(kw, str):
                cleaned = kw.strip().lower()
                if cleaned and cleaned not in normalized_keywords:
                    normalized_keywords.append(cleaned)

        if not normalized_keywords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Keyword trigger requires at least one non-empty keyword."
            )

        return norm_trigger_type, {"keywords": normalized_keywords}

    def _validate_and_normalize_action(
        self, action_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(action_config, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action configuration must be a JSON object."
            )

        pub_cfg = action_config.get("public_reply") or {}
        priv_cfg = action_config.get("private_message") or {}

        pub_enabled = bool(pub_cfg.get("enabled", False))
        priv_enabled = bool(priv_cfg.get("enabled", False))

        if not pub_enabled and not priv_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one action (public reply or private message) must be configured and enabled."
            )

        clean_variations = []
        if pub_enabled:
            variations = pub_cfg.get("variations")
            if not isinstance(variations, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Public reply is enabled but variations list is missing."
                )
            for v in variations:
                if isinstance(v, str) and v.strip():
                    clean_variations.append(v.strip())
            if not clean_variations:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Public reply is enabled but no non-empty reply variations were provided."
                )

        clean_message = None
        if priv_enabled:
            msg = priv_cfg.get("message")
            if not isinstance(msg, str) or not msg.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Private message is enabled but message text is empty."
                )
            clean_message = msg.strip()

        return {
            "public_reply": {
                "enabled": pub_enabled,
                "variations": clean_variations
            },
            "private_message": {
                "enabled": priv_enabled,
                "message": clean_message
            }
        }

    def create_automation(
        self, db: Session, user_id: int, automation_in: AutomationCreate
    ) -> Automation:
        """Create a new automation in DRAFT status after thorough validation."""
        platform = self._validate_platform(automation_in.platform)
        self._validate_social_account(db, user_id, automation_in.social_account_id, platform)
        internal_post_id, external_post_id = self._validate_post_target(
            db=db,
            user_id=user_id,
            platform=platform,
            post_target_type=automation_in.post_target_type or PostTargetType.SPECIFIC_POST.value,
            internal_post_id=automation_in.internal_post_id,
            external_post_id=automation_in.external_post_id
        )
        trigger_type, trigger_config = self._validate_and_normalize_trigger(
            automation_in.trigger_type, automation_in.trigger_config
        )
        action_config = self._validate_and_normalize_action(automation_in.action_config)

        data = {
            "user_id": user_id,
            "social_account_id": automation_in.social_account_id,
            "name": automation_in.name.strip(),
            "platform": platform,
            "status": AutomationStatus.DRAFT.value,
            "post_target_type": automation_in.post_target_type or PostTargetType.SPECIFIC_POST.value,
            "internal_post_id": internal_post_id,
            "external_post_id": external_post_id,
            "trigger_type": trigger_type,
            "trigger_config": trigger_config,
            "action_config": action_config,
            "metadata_json": automation_in.metadata_json or {}
        }
        return automation_repository.create(db, data)

    def get_user_automations(
        self,
        db: Session,
        user_id: int,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        social_account_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Automation]:
        """List automations owned by the authenticated user with optional filtering."""
        query = db.query(Automation).filter(Automation.user_id == user_id)
        if status:
            query = query.filter(Automation.status == status.strip().upper())
        if platform:
            query = query.filter(Automation.platform == platform.strip().lower())
        if social_account_id:
            query = query.filter(Automation.social_account_id == social_account_id)
        return query.order_by(Automation.created_at.desc()).offset(skip).limit(limit).all()

    def get_automation(self, db: Session, automation_id: int, user_id: int) -> Automation:
        """Fetch single automation by ID ensuring user ownership."""
        automation = automation_repository.get_by_id_and_user(db, automation_id, user_id)
        if not automation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Automation not found or access denied."
            )
        return automation

    def update_automation(
        self, db: Session, automation_id: int, user_id: int, automation_in: AutomationUpdate
    ) -> Automation:
        """Update automation fields safely with consistent re-validation."""
        automation = self.get_automation(db, automation_id, user_id)

        update_data: Dict[str, Any] = {}

        # 1. Name update
        if automation_in.name is not None:
            if not automation_in.name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Automation name cannot be empty."
                )
            update_data["name"] = automation_in.name.strip()

        # 2. Platform / Account / Post Target updates
        target_platform = self._validate_platform(automation_in.platform) if automation_in.platform is not None else automation.platform
        target_account_id = automation_in.social_account_id if automation_in.social_account_id is not None else automation.social_account_id
        target_post_target_type = automation_in.post_target_type if automation_in.post_target_type is not None else automation.post_target_type

        needs_account_validation = (automation_in.platform is not None) or (automation_in.social_account_id is not None)
        if needs_account_validation:
            self._validate_social_account(db, user_id, target_account_id, target_platform)
            update_data["platform"] = target_platform
            update_data["social_account_id"] = target_account_id

        needs_post_validation = (
            needs_account_validation
            or (automation_in.internal_post_id is not None)
            or (automation_in.external_post_id is not None)
            or (automation_in.post_target_type is not None)
        )
        if needs_post_validation:
            internal_post_id = automation_in.internal_post_id if automation_in.internal_post_id is not None else automation.internal_post_id
            external_post_id = automation_in.external_post_id if automation_in.external_post_id is not None else automation.external_post_id
            int_id, ext_id = self._validate_post_target(
                db=db,
                user_id=user_id,
                platform=target_platform,
                post_target_type=target_post_target_type,
                internal_post_id=internal_post_id,
                external_post_id=external_post_id
            )
            update_data["post_target_type"] = target_post_target_type
            update_data["internal_post_id"] = int_id
            update_data["external_post_id"] = ext_id

        # 3. Trigger configuration update
        if automation_in.trigger_type is not None or automation_in.trigger_config is not None:
            t_type = automation_in.trigger_type if automation_in.trigger_type is not None else automation.trigger_type
            t_cfg = automation_in.trigger_config if automation_in.trigger_config is not None else automation.trigger_config
            norm_t_type, norm_t_cfg = self._validate_and_normalize_trigger(t_type, t_cfg)
            update_data["trigger_type"] = norm_t_type
            update_data["trigger_config"] = norm_t_cfg

        # 4. Action configuration update
        if automation_in.action_config is not None:
            update_data["action_config"] = self._validate_and_normalize_action(automation_in.action_config)

        # 5. Metadata update
        if automation_in.metadata_json is not None:
            update_data["metadata_json"] = automation_in.metadata_json

        return automation_repository.update(db, automation, update_data)

    def activate_automation(self, db: Session, automation_id: int, user_id: int) -> Automation:
        """
        Activate an automation (DRAFT -> ACTIVE or PAUSED -> ACTIVE).
        Validates completeness of social account, target post, triggers, and actions before activation.
        """
        automation = self.get_automation(db, automation_id, user_id)

        if automation.status == AutomationStatus.ACTIVE.value:
            return automation

        # Run complete validation checks
        platform = self._validate_platform(automation.platform)
        self._validate_social_account(db, user_id, automation.social_account_id, platform)
        self._validate_post_target(
            db=db,
            user_id=user_id,
            platform=platform,
            post_target_type=automation.post_target_type,
            internal_post_id=automation.internal_post_id,
            external_post_id=automation.external_post_id
        )
        self._validate_and_normalize_trigger(automation.trigger_type, automation.trigger_config)
        self._validate_and_normalize_action(automation.action_config)

        return automation_repository.update(db, automation, {"status": AutomationStatus.ACTIVE.value})

    def pause_automation(self, db: Session, automation_id: int, user_id: int) -> Automation:
        """Pause an active automation (ACTIVE -> PAUSED)."""
        automation = self.get_automation(db, automation_id, user_id)

        if automation.status == AutomationStatus.PAUSED.value:
            return automation

        if automation.status == AutomationStatus.DRAFT.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pause a draft automation. Only active automations can be paused."
            )

        return automation_repository.update(db, automation, {"status": AutomationStatus.PAUSED.value})

    def delete_automation(self, db: Session, automation_id: int, user_id: int) -> Dict[str, Any]:
        """Delete an automation and cascade delete related executions."""
        self.get_automation(db, automation_id, user_id)
        automation_repository.delete(db, automation_id)
        return {
            "success": True,
            "message": "Automation deleted successfully",
            "automation_id": automation_id
        }


automation_service = AutomationService()
