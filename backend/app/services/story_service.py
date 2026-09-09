"""
Story Service - Dedicated Isolated Service for Stories Automation.
Integrates with Meta Graph API for Instagram Stories and Facebook Page Stories.

Official Meta Documentation References:
- Instagram Content Publishing API (Stories):
  https://developers.facebook.com/docs/instagram-api/guides/content-publishing/
  Permissions: instagram_basic, instagram_content_publish
  Container Creation Endpoint: POST https://graph.facebook.com/{version}/{ig_user_id}/media (media_type=STORIES)
  Container Status Endpoint: GET https://graph.facebook.com/{version}/{container_id}?fields=status_code,status
  Publishing Endpoint: POST https://graph.facebook.com/{version}/{ig_user_id}/media_publish (creation_id={container_id})
  
- Facebook Page Stories API:
  https://developers.facebook.com/docs/pages-api/page-stories/
  Permissions: pages_show_list, pages_read_engagement, pages_manage_posts
  Image Story Endpoints:
    1. POST https://graph.facebook.com/{version}/{page_id}/photos (published=false, temporary=true)
    2. POST https://graph.facebook.com/{version}/{page_id}/photo_stories (photo_id={photo_id})
  Video Story Endpoint:
    POST https://graph.facebook.com/{version}/{page_id}/video_stories
"""

import logging
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security_encryption import decrypt_token
from app.core.logging_config import sanitize_url
from app.models.story import Story, StoryStatus
from app.models.social_account import SocialAccount
from app.models.brand import BrandProfile
from app.repositories.story_repository import story_repo
from app.repositories.social_account_repository import social_account_repo
from app.repositories.audit_repository import audit_repo
from app.schemas.story import StoryCreate, StoryUpdate, StoryValidationResult
from app.services.media_service import upload_base64_to_public_https
from app.services.meta_service import meta_service
from app.core.story_url_helper import (
    sanitize_instagram_username,
    build_instagram_story_url,
    is_valid_instagram_story_url,
    is_valid_facebook_story_url,
    resolve_instagram_username_from_social_account,
)

logger = logging.getLogger(__name__)


def classify_story_error(err_str: str) -> Tuple[str, str]:
    """Classify technical exceptions into user-friendly error codes and messages."""
    err_lower = err_str.lower()
    if "timeout" in err_lower or "timed out" in err_lower:
        return "PUBLISH_TIMEOUT", "Story publishing process timed out. Please try again."
    if "token" in err_lower or "expired" in err_lower or "session" in err_lower or "oauth" in err_lower:
        return "TOKEN_EXPIRED", "Account authorization expired. Please reconnect this account."
    if "creator" in err_lower:
        return "CREATOR_UNSUPPORTED", err_str
    if "permission" in err_lower or "access" in err_lower or "denied" in err_lower:
        return "PERMISSION_ERROR", "Insufficient permissions for Story publishing. Reconnect account with required scopes (instagram_content_publish / pages_manage_posts)."
    if "rate" in err_lower or "limit" in err_lower or "429" in err_lower:
        return "RATE_LIMIT", "Meta API rate limit reached. Retrying automatically shortly."
    if "media" in err_lower or "aspect ratio" in err_lower or "format" in err_lower or "video" in err_lower:
        return "INVALID_MEDIA", f"Story media error: {err_str[:200]}"
    if "not found" in err_lower or "no connected" in err_lower:
        return "ACCOUNT_NOT_FOUND", err_str[:200]
    return "PLATFORM_ERROR", f"Meta Story API error: {err_str[:200]}"


class StoryService:
    BASE_URL = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

    def validate_story_media(self, media_url: str, media_type: str) -> Tuple[bool, List[str], List[str]]:
        """Validate media URL, format, and protocol for Story requirements."""
        errors: List[str] = []
        warnings: List[str] = []

        if not media_url:
            errors.append("Story media URL is required.")
            return False, errors, warnings

        # Protocol check
        if not (media_url.startswith("http://") or media_url.startswith("https://") or media_url.startswith("data:") or media_url.startswith("/uploads/")):
            errors.append("Story media URL must be a valid HTTPS or HTTP URL.")

        # Media type check
        norm_type = media_type.lower() if media_type else "image"
        if norm_type not in ["image", "video"]:
            errors.append("Unsupported media type for Story. Must be 'image' or 'video'.")

        # Format / Extension hints
        clean_url = media_url.split("?")[0].lower()
        if norm_type == "video":
            valid_video_exts = [".mp4", ".mov", ".webm", ".m4v"]
            if not any(clean_url.endswith(ext) for ext in valid_video_exts) and not media_url.startswith("data:video"):
                warnings.append("Video Stories should ideally be MP4 or MOV format encoded with H.264 / AAC.")
        elif norm_type == "image":
            valid_img_exts = [".jpg", ".jpeg", ".png", ".webp"]
            if not any(clean_url.endswith(ext) for ext in valid_img_exts) and not media_url.startswith("data:image"):
                warnings.append("Image Stories should ideally be JPG or PNG format.")

        warnings.append("Recommended aspect ratio for Stories is 9:16 (1080x1920 pixels). Supported range is 9:16 to 16:9.")

        return len(errors) == 0, errors, warnings

    def validate_account_capability(self, account: SocialAccount, target_platform: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a social account is capable of publishing Stories according to Meta API rules.
        Differentiates Instagram Business vs Creator accounts.
        """
        if not account:
            return False, "Social account does not exist."

        if account.status == "TOKEN_EXPIRED":
            return False, f"{account.account_name} ({account.platform}) token is expired. Please reconnect."

        if account.status == "REVOKED":
            return False, f"{account.account_name} ({account.platform}) authorization is revoked."

        meta_json = account.metadata_json or {}

        if target_platform == "instagram":
            if account.platform != "instagram":
                return False, f"Account {account.account_name} is not an Instagram account."

            if not account.account_id or account.account_id.startswith("user_"):
                return False, f"Instagram account {account.account_name} must be a Professional or Business account to publish Stories."

            # Differentiate Creator vs Business accounts when flagged in metadata
            account_type = str(meta_json.get("account_type", "")).upper()
            if account_type == "CREATOR" and not meta_json.get("creator_story_publishing_supported", False):
                return False, f"Instagram account {account.account_name} is a Creator account which does not support Story publishing under this authorization. Please use an Instagram Business account."

        elif target_platform == "facebook":
            if account.platform != "facebook":
                return False, f"Account {account.account_name} is not a Facebook Page account."
            if not account.account_id:
                return False, f"Facebook Page ID is missing for {account.account_name}."

        else:
            return False, f"Unsupported platform: {target_platform}"

        return True, None

    def _validate_story_target_accounts(
        self,
        db: Session,
        user_id: int,
        target_account_ids: List[int],
        require_non_empty: bool = True
    ) -> List[SocialAccount]:
        """
        Validate that all specified target_account_ids exist, belong strictly to user_id,
        and are capable of publishing Stories.
        """
        if not target_account_ids:
            if require_non_empty:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No Story destinations selected. Please select at least one connected SocialAccount."
                )
            return []

        # Query all requested account IDs
        accounts = db.query(SocialAccount).filter(SocialAccount.id.in_(target_account_ids)).all()
        account_map = {acc.id: acc for acc in accounts}

        # Verify all IDs exist
        for aid in target_account_ids:
            if aid not in account_map:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target SocialAccount ID {aid} not found."
                )

        # Security check: verify all accounts belong to the current user
        for acc in accounts:
            if acc.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Unauthorized: SocialAccount ID {acc.id} does not belong to the authenticated user."
                )

        # Validate Story capability for each account
        for acc in accounts:
            capable, reason = self.validate_account_capability(acc, acc.platform)
            if not capable:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Account '{acc.account_name}' ({acc.platform}) is not capable of Story publishing: {reason}"
                )

        return [account_map[aid] for aid in target_account_ids]

    def validate_story_preflight(self, db: Session, story_in: StoryCreate, user_id: int) -> StoryValidationResult:
        """Perform comprehensive preflight checks on media and explicitly selected target accounts."""
        all_errors: List[str] = []
        all_warnings: List[str] = []
        account_checks: List[Dict[str, Any]] = []

        target_ids = story_in.target_account_ids or []
        logger.info(f"[STORY_PREFLIGHT] user_id={user_id} brand_id={story_in.brand_id} media_type={story_in.media_type} target_account_ids={target_ids} count={len(target_ids)}")

        # 1. Media validation
        is_media_valid, m_errors, m_warnings = self.validate_story_media(story_in.media_url, story_in.media_type)
        all_errors.extend(m_errors)
        all_warnings.extend(m_warnings)

        # 2. Selected target accounts check
        if not target_ids:
            all_errors.append("No Story destinations selected. Please select at least one account.")
            all_warnings.append("Select at least one connected Facebook Page or Instagram Business account.")
            return StoryValidationResult(
                is_valid=False,
                errors=all_errors,
                warnings=all_warnings,
                account_checks=[]
            )

        for aid in target_ids:
            acc = db.query(SocialAccount).filter(SocialAccount.id == aid).first()
            if not acc:
                all_errors.append(f"Target account ID {aid} does not exist.")
                account_checks.append({
                    "account_id": aid,
                    "account_name": None,
                    "platform": None,
                    "capable": False,
                    "reason": f"SocialAccount ID {aid} not found."
                })
            elif acc.user_id != user_id:
                all_errors.append(f"Target account ID {aid} does not belong to the current user.")
                account_checks.append({
                    "account_id": aid,
                    "account_name": None,
                    "platform": acc.platform,
                    "capable": False,
                    "reason": "Unauthorized access to account."
                })
            else:
                capable, reason = self.validate_account_capability(acc, acc.platform)
                account_checks.append({
                    "account_id": acc.id,
                    "account_name": acc.account_name,
                    "platform": acc.platform,
                    "capable": capable,
                    "reason": reason
                })
                if not capable and reason:
                    all_errors.append(f"{acc.account_name} ({acc.platform}): {reason}")

        return StoryValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            account_checks=account_checks
        )

    def publish_instagram_story(
        self,
        account: SocialAccount,
        media_url: str,
        is_video: bool = False,
        story_id: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """Publish an Image or Video Story to Instagram via Meta Graph API."""
        start_time = time.time()
        token = decrypt_token(account.access_token) or account.access_token
        ig_user_id = account.account_id
        story_log_id = story_id if story_id is not None else "n/a"

        # Resolve clean Instagram username
        username = resolve_instagram_username_from_social_account(account)

        # Sandbox / Mock Mode
        is_mock = (settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production") or token.startswith("sandbox") or token.startswith("mock") or ig_user_id == "sandbox"
        if is_mock:
            logger.info(f"[IG_STORY_PUBLISH] Executing Sandbox/Mock Instagram Story Publish for {ig_user_id}.")
            mock_user = username or "mock_instagram_user"
            mock_url = build_instagram_story_url(mock_user)
            return {
                "id": f"ig_story_mock_{int(time.time())}",
                "container_id": f"ig_container_mock_{int(time.time())}",
                "status": "published_sandbox",
                "url": mock_url,
                "username": mock_user
            }

        # Resolve public HTTPS media URL
        final_url = media_url
        if final_url.startswith("data:") or final_url.startswith("blob:"):
            final_url = upload_base64_to_public_https(final_url) or final_url
            if final_url.startswith("data:") or final_url.startswith("blob:"):
                raise Exception("Instagram Story publishing requires a publicly accessible HTTPS media URL.")

        logger.info(f"[IG_STORY_PUBLISH] Creating IG Story Container | story_id={story_log_id} | ig_user_id={ig_user_id} | is_video={is_video} | media_url={sanitize_url(final_url)}")

        # Step 1: Create Container with media_type=STORIES
        container_url = f"{self.BASE_URL}/{ig_user_id}/media"
        container_params = {
            "media_type": "STORIES",
            "access_token": token
        }
        if is_video:
            container_params["video_url"] = final_url
        else:
            container_params["image_url"] = final_url

        try:
            res = requests.post(container_url, data=container_params, timeout=30)
            res_data = res.json()
        except Exception as e:
            logger.error(f"[IG_STORY_PUBLISH] Container creation network error: {e}")
            raise Exception(f"Instagram Story container creation failed: {e}")

        if res.status_code != 200:
            err = res_data.get("error", {})
            err_msg = err.get("message", "Instagram API Container Creation Error")
            raise Exception(f"Instagram Story Container Error ({res.status_code}) [code={err.get('code')}]: {err_msg}")

        container_id = res_data.get("id")
        if not container_id:
            raise Exception(f"Instagram API returned no container ID: {res_data}")

        logger.info(f"[IG_STORY_CONTAINER_CREATED] story_id={story_log_id} container_id={container_id}")

        # Step 2: Robust bounded polling for container readiness (both images and videos)
        max_attempts = 30 if is_video else 20
        poll_interval = 3.0 if is_video else 2.0
        container_poll_start = time.time()
        is_ready = False
        last_status_code = "UNKNOWN"

        for attempt in range(1, max_attempts + 1):
            try:
                status_res = requests.get(
                    f"{self.BASE_URL}/{container_id}",
                    params={"fields": "status_code,status", "access_token": token},
                    timeout=10
                )
                if status_res.status_code == 200:
                    s_data = status_res.json()
                    s_code = s_data.get("status_code", "UNKNOWN")
                    last_status_code = s_code
                    elapsed = round(time.time() - container_poll_start, 2)
                    logger.info(
                        f"[IG_STORY_CONTAINER_STATUS] story_id={story_log_id} container_id={container_id} "
                        f"status={s_code} attempt={attempt}/{max_attempts} elapsed={elapsed}s"
                    )

                    if s_code == "FINISHED":
                        is_ready = True
                        logger.info(f"[IG_STORY_CONTAINER_READY] story_id={story_log_id} container_id={container_id} elapsed={elapsed}s")
                        break
                    elif s_code in ["ERROR", "EXPIRED"]:
                        err_details = s_data.get("status") or s_code
                        logger.error(f"[IG_STORY_PUBLISH_FAIL] story_id={story_log_id} container_id={container_id} status={s_code} error={err_details}")
                        raise Exception(f"Instagram Story container failed processing with status: {s_code} ({err_details})")
                else:
                    logger.warning(f"[IG_STORY_CONTAINER_STATUS] status_check_http_error={status_res.status_code}")
            except Exception as poll_err:
                if "Instagram Story container failed processing" in str(poll_err):
                    raise
                logger.warning(f"[IG_STORY_PUBLISH] Status poll network warning: {poll_err}")

            if attempt < max_attempts:
                time.sleep(poll_interval)

        if not is_ready:
            elapsed = round(time.time() - container_poll_start, 2)
            logger.error(
                f"[IG_STORY_PUBLISH_FAIL] story_id={story_log_id} container_id={container_id} "
                f"status=TIMEOUT last_status={last_status_code} error=Container processing timed out after {elapsed}s"
            )
            raise Exception(f"Instagram Story container {container_id} processing timed out after {elapsed}s (last status: {last_status_code}). Media is not ready for publishing.")

        # Step 3: Publish container once confirmed FINISHED/ready
        publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
        try:
            pub_res = requests.post(
                publish_url,
                data={"creation_id": container_id, "access_token": token},
                timeout=30
            )
            pub_data = pub_res.json()
        except Exception as e:
            logger.error(f"[IG_STORY_PUBLISH_FAIL] story_id={story_log_id} container_id={container_id} status=FAIL error=Media publish network error: {e}")
            raise Exception(f"Instagram Story publish network error: {e}")

        if pub_res.status_code != 200:
            err = pub_data.get("error", {})
            err_msg = err.get("message", "Instagram API Media Publish Error")
            logger.error(f"[IG_STORY_PUBLISH_FAIL] story_id={story_log_id} container_id={container_id} status=FAIL error={err_msg} [code={err.get('code')}]")
            raise Exception(f"Instagram Story Publish Error ({pub_res.status_code}) [code={err.get('code')}]: {err_msg}")

        media_id = pub_data.get("id")
        if not media_id:
            logger.error(f"[IG_STORY_PUBLISH_FAIL] story_id={story_log_id} container_id={container_id} status=FAIL error=Missing media ID in response")
            raise Exception(f"Instagram API returned success but missing media ID: {pub_data}")

        total_elapsed = round(time.time() - start_time, 2)
        logger.info(f"[IG_STORY_PUBLISH_SUCCESS] story_id={story_log_id} container_id={container_id} meta_id={media_id} elapsed={total_elapsed}s")

        # Step 4: Resolve legitimate public viewing URL
        ig_story_url = None
        try:
            p_res = requests.get(
                f"{self.BASE_URL}/{media_id}",
                params={"fields": "permalink", "access_token": token},
                timeout=10
            )
            if p_res.status_code == 200:
                cand_permalink = p_res.json().get("permalink")
                if cand_permalink and is_valid_instagram_story_url(cand_permalink):
                    ig_story_url = cand_permalink
        except Exception as p_err:
            logger.debug(f"[IG_STORY_URL_QUERY] Permalink query notice: {p_err}")

        # If direct permalink is not returned (standard for ephemeral IG stories), resolve via username
        if not ig_story_url:
            if not username and not is_mock:
                try:
                    u_res = requests.get(
                        f"{self.BASE_URL}/{ig_user_id}",
                        params={"fields": "username", "access_token": token},
                        timeout=10
                    )
                    if u_res.status_code == 200:
                        raw_u = u_res.json().get("username")
                        username = sanitize_instagram_username(raw_u)
                        if username and isinstance(account.metadata_json, dict):
                            account.metadata_json["username"] = username
                except Exception as u_err:
                    logger.debug(f"[IG_USERNAME_QUERY] Notice: {u_err}")

            if username:
                ig_story_url = build_instagram_story_url(username)
            else:
                ig_story_url = None

        final_ig_url = ig_story_url if is_valid_instagram_story_url(ig_story_url) else None

        return {
            "id": str(media_id),
            "container_id": str(container_id),
            "status": "published",
            "url": final_ig_url,
            "username": username
        }

    def publish_facebook_story(
        self,
        account: SocialAccount,
        media_url: str,
        is_video: bool = False
    ) -> Dict[str, Any]:
        """Publish an Image or Video Story to a Facebook Page via Meta Graph API."""
        token = decrypt_token(account.access_token) or account.access_token
        page_id = account.account_id

        # Sandbox / Mock Mode
        is_mock = (settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production") or token.startswith("sandbox") or token.startswith("mock") or page_id == "sandbox"
        if is_mock:
            logger.info(f"[FB_STORY_PUBLISH] Executing Sandbox/Mock Facebook Story Publish for {page_id}.")
            mock_url = f"https://www.facebook.com/stories/mock_page_{int(time.time())}"
            return {
                "id": f"fb_story_mock_{int(time.time())}",
                "status": "published_sandbox",
                "url": mock_url,
                "page_url": f"https://www.facebook.com/{page_id}"
            }

        final_url = media_url
        if final_url.startswith("data:") or final_url.startswith("blob:"):
            final_url = upload_base64_to_public_https(final_url) or final_url
            if final_url.startswith("data:") or final_url.startswith("blob:"):
                raise Exception("Facebook Story publishing requires a publicly accessible HTTPS media URL.")

        logger.info(f"[FB_STORY_PUBLISH] Publishing FB Story | page_id={page_id} | is_video={is_video} | media_url={sanitize_url(final_url)}")

        if not is_video:
            # Step 1: Upload photo unlisted (published=false, temporary=true)
            photo_url = f"{self.BASE_URL}/{page_id}/photos"
            try:
                upload_res = requests.post(
                    photo_url,
                    data={
                        "url": final_url,
                        "published": "false",
                        "temporary": "true",
                        "access_token": token
                    },
                    timeout=30
                )
                upload_data = upload_res.json()
            except Exception as e:
                logger.error(f"[FB_STORY_PUBLISH] Photo upload error: {e}")
                raise Exception(f"Facebook Story photo upload failed: {e}")

            if upload_res.status_code != 200:
                err = upload_data.get("error", {})
                raise Exception(f"Facebook Story Photo Upload Error ({upload_res.status_code}): {err.get('message', 'Upload error')}")

            photo_id = upload_data.get("id")
            if not photo_id:
                raise Exception(f"Facebook photo upload missing photo ID: {upload_data}")

            # Step 2: Publish to photo_stories
            story_url = f"{self.BASE_URL}/{page_id}/photo_stories"
            try:
                story_res = requests.post(
                    story_url,
                    data={"photo_id": photo_id, "access_token": token},
                    timeout=30
                )
                story_data = story_res.json()
            except Exception as e:
                logger.error(f"[FB_STORY_PUBLISH] Photo story publish error: {e}")
                raise Exception(f"Facebook photo story publish failed: {e}")

            if story_res.status_code != 200:
                err = story_data.get("error", {})
                raise Exception(f"Facebook Photo Story Error ({story_res.status_code}): {err.get('message', 'Publish error')}")

            story_id = story_data.get("id") or story_data.get("post_id") or str(photo_id)
            fb_story_url = None
            try:
                p_res = requests.get(
                    f"{self.BASE_URL}/{story_id}",
                    params={"fields": "permalink_url,link", "access_token": token},
                    timeout=10
                )
                if p_res.status_code == 200:
                    fb_data = p_res.json()
                    cand_url = fb_data.get("permalink_url") or fb_data.get("link")
                    if cand_url and is_valid_facebook_story_url(cand_url):
                        fb_story_url = cand_url
            except Exception as p_err:
                logger.debug(f"[FB_STORY_URL_QUERY] Permlink query notice: {p_err}")

            # If Meta does not provide a legitimate public individual Story permalink,
            # DO NOT generate https://www.facebook.com/{page_id} as a Story URL!
            final_fb_url = fb_story_url if is_valid_facebook_story_url(fb_story_url) else None

            return {
                "id": str(story_id),
                "photo_id": str(photo_id),
                "status": "published",
                "url": final_fb_url,
                "page_url": f"https://www.facebook.com/{page_id}"
            }
        else:
            # Video Story
            video_url = f"{self.BASE_URL}/{page_id}/videos"
            try:
                video_res = requests.post(
                    video_url,
                    data={
                        "file_url": final_url,
                        "published": "false",
                        "video_state": "PUBLISHED",
                        "access_token": token
                    },
                    timeout=settings.META_VIDEO_UPLOAD_TIMEOUT_SECONDS
                )
                video_data = video_res.json()
            except Exception as e:
                logger.error(f"[FB_STORY_PUBLISH] Video upload error: {e}")
                raise Exception(f"Facebook Story video upload failed: {e}")

            if video_res.status_code != 200:
                err = video_data.get("error", {})
                raise Exception(f"Facebook Video Story Error ({video_res.status_code}): {err.get('message', 'Video upload error')}")

            vid_id = video_data.get("id")
            if not vid_id:
                raise Exception(f"Facebook video upload missing video ID: {video_data}")

            # Publish to video_stories endpoint
            v_story_url = f"{self.BASE_URL}/{page_id}/video_stories"
            try:
                v_story_res = requests.post(
                    v_story_url,
                    data={"video_id": vid_id, "access_token": token},
                    timeout=30
                )
                v_story_data = v_story_res.json()
            except Exception as e:
                logger.warning(f"[FB_STORY_PUBLISH] Direct video_stories publish endpoint notice: {e}")
                v_story_data = {"id": str(vid_id)}

            story_id = v_story_data.get("id") or str(vid_id)
            fb_story_url = None
            try:
                p_res = requests.get(
                    f"{self.BASE_URL}/{story_id}",
                    params={"fields": "permalink_url,link", "access_token": token},
                    timeout=10
                )
                if p_res.status_code == 200:
                    fb_data = p_res.json()
                    cand_url = fb_data.get("permalink_url") or fb_data.get("link")
                    if cand_url and is_valid_facebook_story_url(cand_url):
                        fb_story_url = cand_url
            except Exception as p_err:
                logger.debug(f"[FB_STORY_URL_QUERY] Permlink query notice: {p_err}")

            final_fb_url = fb_story_url if is_valid_facebook_story_url(fb_story_url) else None

            return {
                "id": str(story_id),
                "video_id": str(vid_id),
                "status": "published",
                "url": final_fb_url,
                "page_url": f"https://www.facebook.com/{page_id}"
            }

    def create_story(self, db: Session, story_in: StoryCreate, user_id: int) -> Story:
        """Create a new story record (DRAFT, SCHEDULED, or to be published)."""
        brand = db.query(BrandProfile).filter(
            BrandProfile.id == story_in.brand_id,
            BrandProfile.user_id == user_id
        ).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand profile ID {story_in.brand_id} not found."
            )

        # Validate media URL and type
        is_valid, errors, _ = self.validate_story_media(story_in.media_url, story_in.media_type)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=" | ".join(errors)
            )

        target_ids = story_in.target_account_ids or []
        status_val = story_in.status or StoryStatus.DRAFT.value

        if status_val in [StoryStatus.SCHEDULED.value, StoryStatus.PUBLISHING.value] and not target_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target destination accounts are required to schedule or publish a Story."
            )

        validated_accounts: List[SocialAccount] = []
        if target_ids:
            validated_accounts = self._validate_story_target_accounts(
                db=db,
                user_id=user_id,
                target_account_ids=target_ids,
                require_non_empty=True
            )
            platforms = list(dict.fromkeys([acc.platform for acc in validated_accounts]))
        else:
            platforms = []

        story = Story(
            brand_id=story_in.brand_id,
            user_id=user_id,
            title=story_in.title,
            caption=story_in.caption,
            media_url=story_in.media_url,
            media_type=story_in.media_type or "image",
            thumbnail_url=story_in.thumbnail_url,
            target_account_ids=target_ids,
            platforms=platforms,
            status=status_val,
            scheduled_at=story_in.scheduled_at
        )
        db.add(story)
        db.commit()
        db.refresh(story)

        audit_repo.log(
            db=db,
            user_id=user_id,
            action="STORY_CREATED",
            resource_type="Story",
            resource_id=story.id,
            details={
                "title": story.title,
                "target_account_ids": story.target_account_ids,
                "platforms": story.platforms,
                "status": story.status
            }
        )
        return story

    def get_story(self, db: Session, story_id: int, user_id: int) -> Story:
        """Get single story ensuring strict tenant authorization."""
        story = story_repo.get(db, story_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found."
            )
        if story.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this Story."
            )
        return story

    def get_user_stories(
        self,
        db: Session,
        user_id: int,
        brand_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Story]:
        """Fetch user stories with optional brand and status filtering."""
        self.check_and_publish_due_stories(db, user_id)
        if brand_id:
            return story_repo.get_by_brand(db, brand_id, status)
        return story_repo.get_by_user(db, user_id, status)

    def update_story(self, db: Session, story_id: int, user_id: int, story_in: StoryUpdate) -> Story:
        """Update draft or failed story fields."""
        story = self.get_story(db, story_id, user_id)
        if story.status in [StoryStatus.PUBLISHING.value, StoryStatus.PUBLISHED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update Story in '{story.status}' status."
            )

        update_data = story_in.model_dump(exclude_unset=True)
        if "media_url" in update_data or "media_type" in update_data:
            m_url = update_data.get("media_url", story.media_url)
            m_type = update_data.get("media_type", story.media_type)
            is_valid, errors, _ = self.validate_story_media(m_url, m_type)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=" | ".join(errors)
                )

        if "target_account_ids" in update_data and update_data["target_account_ids"] is not None:
            target_ids = update_data["target_account_ids"]
            if target_ids:
                validated_accounts = self._validate_story_target_accounts(
                    db=db,
                    user_id=user_id,
                    target_account_ids=target_ids,
                    require_non_empty=True
                )
                update_data["platforms"] = list(dict.fromkeys([acc.platform for acc in validated_accounts]))
            else:
                update_data["platforms"] = []

        updated = story_repo.update(db, story, update_data)
        audit_repo.log(
            db=db,
            user_id=user_id,
            action="STORY_UPDATED",
            resource_type="Story",
            resource_id=story_id,
            details=update_data
        )
        return updated

    def delete_story(self, db: Session, story_id: int, user_id: int) -> dict:
        """
        Safely delete a story by ID.
        - Verifies user ownership (raises 404 if not found or unauthorized).
        - For scheduled stories: cancels scheduled execution safely, then deletes.
        - For published stories: finds all associated external Meta targets,
          attempts external Meta Graph API deletion for each published target, and handles partial failures.
        - If all external deletions succeed: removes local story record.
        - If any external deletion fails: retains local story record, records partial state, and returns details.
        """
        story = story_repo.get(db, story_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found."
            )
        if story.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this Story."
            )

        # 1. Gather all external targets for this story
        targets = []
        user_accs = db.query(SocialAccount).filter(SocialAccount.user_id == user_id).all()
        acc_map = {acc.id: acc for acc in user_accs}

        if story.fb_story_id:
            # Find the target FB social account
            fb_acc = None
            for aid in (story.target_account_ids or []):
                acc = acc_map.get(aid)
                if acc and acc.platform == "facebook":
                    fb_acc = acc
                    break
            if not fb_acc:
                fb_acc = next((a for a in user_accs if a.platform == "facebook" and a.brand_id == story.brand_id), None) or next((a for a in user_accs if a.platform == "facebook"), None)
            
            targets.append({
                "platform": "facebook",
                "social_account": fb_acc,
                "external_story_id": story.fb_story_id,
            })

        if story.ig_story_id:
            # Find the target IG social account
            ig_acc = None
            for aid in (story.target_account_ids or []):
                acc = acc_map.get(aid)
                if acc and acc.platform == "instagram":
                    ig_acc = acc
                    break
            if not ig_acc:
                ig_acc = next((a for a in user_accs if a.platform == "instagram" and a.brand_id == story.brand_id), None) or next((a for a in user_accs if a.platform == "instagram"), None)
            
            targets.append({
                "platform": "instagram",
                "social_account": ig_acc,
                "external_story_id": story.ig_story_id,
            })

        # 2. If scheduled, cancel scheduled state before proceeding
        if story.status == StoryStatus.SCHEDULED.value:
            logger.info(f"[STORY_DELETE_TRACE] Cancelling scheduled story ID={story.id}")
            story.scheduled_at = None
            story.status = StoryStatus.DRAFT.value
            db.commit()

        # 3. Attempt external deletion for all targets
        logger.info(f"[STORY_DELETE_START] story_id={story.id} user_id={user_id} target_count={len(targets)}")
        details = []
        deleted_count = 0
        failed_count = 0

        for t in targets:
            platform = t["platform"]
            ext_id = t["external_story_id"]
            soc_acc = t["social_account"]
            account_name = soc_acc.account_name if soc_acc else None
            account_id_str = soc_acc.account_id if soc_acc else None

            logger.info(f"[STORY_PLATFORM_DELETE] story_id={story.id} platform={platform} external_id={ext_id}")

            if not soc_acc or not soc_acc.access_token:
                err_msg = f"Social account not found or access token unavailable for {platform}"
                logger.error(f"[STORY_PLATFORM_DELETE_FAIL] story_id={story.id} platform={platform} external_id={ext_id} error={err_msg}")
                failed_count += 1
                details.append({
                    "platform": platform,
                    "account_id": account_id_str,
                    "account_name": account_name,
                    "external_story_id": ext_id,
                    "success": False,
                    "error": err_msg
                })
                continue

            raw_token = decrypt_token(soc_acc.access_token) or soc_acc.access_token
            if not raw_token:
                err_msg = f"Failed to decrypt access token for {platform}"
                logger.error(f"[STORY_PLATFORM_DELETE_FAIL] story_id={story.id} platform={platform} external_id={ext_id} error={err_msg}")
                failed_count += 1
                details.append({
                    "platform": platform,
                    "account_id": account_id_str,
                    "account_name": account_name,
                    "external_story_id": ext_id,
                    "success": False,
                    "error": err_msg
                })
                continue

            try:
                if platform == "facebook":
                    meta_service.delete_facebook_post(ext_id, raw_token)
                    story.fb_story_id = None
                    story.fb_story_url = None
                    story.fb_page_url = None
                elif platform == "instagram":
                    meta_service.delete_instagram_media(ext_id, raw_token)
                    story.ig_story_id = None
                    story.ig_story_url = None
                    story.ig_username = None
                else:
                    raise Exception(f"Unsupported platform: {platform}")

                deleted_count += 1
                logger.info(f"[STORY_PLATFORM_DELETE_SUCCESS] story_id={story.id} platform={platform} external_id={ext_id}")
                details.append({
                    "platform": platform,
                    "account_id": account_id_str,
                    "account_name": account_name,
                    "external_story_id": ext_id,
                    "success": True,
                    "error": None
                })
            except Exception as delete_err:
                err_str = str(delete_err)
                logger.error(f"[STORY_PLATFORM_DELETE_FAIL] story_id={story.id} platform={platform} external_id={ext_id} error={err_str}")
                failed_count += 1
                details.append({
                    "platform": platform,
                    "account_id": account_id_str,
                    "account_name": account_name,
                    "external_story_id": ext_id,
                    "success": False,
                    "error": err_str
                })

        # 4. Handle Deletion Outcome
        if failed_count > 0:
            story.last_error = f"Deletion failed for {failed_count} external target(s)."
            db.commit()

            audit_repo.log(
                db=db,
                user_id=user_id,
                action="STORY_DELETE_FAILED",
                resource_type="Story",
                resource_id=story.id,
                details={"deleted_targets": deleted_count, "failed_targets": failed_count, "target_details": details}
            )
            logger.info(f"[STORY_DELETE_COMPLETED] story_id={story.id} status=PARTIAL_FAILURE deleted={deleted_count} failed={failed_count}")

            return {
                "success": False,
                "message": f"Failed to delete {failed_count} of {len(targets)} external target(s). Local story retained.",
                "story_id": story_id,
                "deleted_external_targets": deleted_count,
                "failed_external_targets": failed_count,
                "details": details
            }

        audit_repo.log(
            db=db,
            user_id=user_id,
            action="STORY_DELETED",
            resource_type="Story",
            resource_id=story_id,
            details={"deleted_external_targets": deleted_count, "target_details": details}
        )

        db.delete(story)
        db.commit()
        logger.info(f"[STORY_DELETE_COMPLETED] story_id={story_id} status=SUCCESS deleted={deleted_count}")

        return {
            "success": True,
            "message": "Story and external targets deleted successfully." if targets else "Story deleted successfully.",
            "story_id": story_id,
            "deleted_external_targets": deleted_count,
            "failed_external_targets": 0,
            "details": details
        }

    def schedule_story(self, db: Session, story_id: int, user_id: int, scheduled_at: datetime) -> Story:
        """Schedule story for future publication using persisted target_account_ids."""
        story = self.get_story(db, story_id, user_id)
        if not story.target_account_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule Story with zero target destination accounts."
            )

        now_utc = datetime.now(timezone.utc)
        sched = scheduled_at.replace(tzinfo=timezone.utc) if scheduled_at.tzinfo is None else scheduled_at

        if sched <= now_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled publishing time must be in the future."
            )

        story.scheduled_at = sched
        story.status = StoryStatus.SCHEDULED.value
        story.last_error = None
        db.commit()
        db.refresh(story)

        audit_repo.log(
            db=db,
            user_id=user_id,
            action="STORY_SCHEDULED",
            resource_type="Story",
            resource_id=story_id,
            details={
                "scheduled_at": sched.isoformat(),
                "target_account_ids": story.target_account_ids
            }
        )
        return story

    def publish_story(self, db: Session, story_id: int, user_id: Optional[int] = None) -> Story:
        """Execute immediate Story publishing ONLY across explicitly targeted SocialAccount records."""
        start_time = time.time()
        story = story_repo.get(db, story_id)
        if not story:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Story {story_id} not found.")

        if user_id and story.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to publish this Story.")

        # Idempotency Protection: If already published, do NOT repeat Meta API calls
        if story.status == StoryStatus.PUBLISHED.value:
            logger.info(
                f"[STORY_PUBLISH_ALREADY_PUBLISHED] story_id={story_id} user_id={story.user_id} "
                f"status=PUBLISHED. Returning persisted published story without repeating Meta API calls."
            )
            return story

        target_ids = story.target_account_ids or []
        logger.info(f"[STORY_PUBLISH_START] story_id={story_id} user_id={story.user_id} target_account_ids={target_ids} count={len(target_ids)}")

        if not target_ids:
            story.status = StoryStatus.FAILED.value
            story.last_error = "Story has no target destination accounts configured."
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Story has no target destination accounts configured."
            )

        story.status = StoryStatus.PUBLISHING.value
        db.commit()

        # Fetch exact target accounts belonging strictly to the story author
        target_accounts = db.query(SocialAccount).filter(
            SocialAccount.id.in_(target_ids),
            SocialAccount.user_id == story.user_id
        ).all()
        account_map = {acc.id: acc for acc in target_accounts}

        is_video = story.media_type.lower() == "video"
        successful_account_ids: List[int] = []
        failed_account_ids: List[int] = []
        successful_platforms: List[str] = []
        errors: List[str] = []

        for aid in target_ids:
            acc = account_map.get(aid)
            if not acc:
                err_msg = f"Target account ID {aid} not found or not owned by user."
                errors.append(err_msg)
                failed_account_ids.append(aid)
                continue

            capable, cap_err = self.validate_account_capability(acc, acc.platform)
            if not capable:
                err_msg = f"{acc.account_name} ({acc.platform}) capability error: {cap_err}"
                errors.append(err_msg)
                failed_account_ids.append(aid)
                continue

            acc_start_time = time.time()
            logger.info(f"[STORY_META_PUBLISH_START] story_id={story.id} account_db_id={acc.id} platform={acc.platform} external_id={acc.account_id} media_type={story.media_type}")

            try:
                if acc.platform == "facebook":
                    res = self.publish_facebook_story(
                        account=acc,
                        media_url=story.media_url,
                        is_video=is_video
                    )
                    story.fb_story_id = str(res.get("id"))
                    story.fb_story_url = res.get("url")
                    story.fb_page_url = res.get("page_url")
                    successful_account_ids.append(acc.id)
                    if "facebook" not in successful_platforms:
                        successful_platforms.append("facebook")
                    acc_duration = round(time.time() - acc_start_time, 2)
                    logger.info(f"[STORY_META_PUBLISH_SUCCESS] story_id={story.id} account_db_id={acc.id} platform=facebook meta_id={story.fb_story_id} duration={acc_duration}s url={story.fb_story_url}")
                elif acc.platform == "instagram":
                    res = self.publish_instagram_story(
                        account=acc,
                        media_url=story.media_url,
                        is_video=is_video,
                        story_id=story.id
                    )
                    story.ig_container_id = str(res.get("container_id", ""))
                    story.ig_story_id = str(res.get("id"))
                    story.ig_story_url = res.get("url")
                    story.ig_username = res.get("username")
                    successful_account_ids.append(acc.id)
                    if "instagram" not in successful_platforms:
                        successful_platforms.append("instagram")
                    acc_duration = round(time.time() - acc_start_time, 2)
                    logger.info(f"[STORY_META_PUBLISH_SUCCESS] story_id={story.id} account_db_id={acc.id} platform=instagram meta_id={story.ig_story_id} duration={acc_duration}s url={story.ig_story_url}")
                else:
                    err_msg = f"Unsupported platform '{acc.platform}' for account ID {aid}."
                    errors.append(err_msg)
                    failed_account_ids.append(aid)
            except Exception as e:
                acc_duration = round(time.time() - acc_start_time, 2)
                logger.error(f"[STORY_META_PUBLISH_FAIL] story_id={story.id} account_db_id={acc.id} platform={acc.platform} duration={acc_duration}s error={e}")
                _, clean_msg = classify_story_error(str(e))
                errors.append(f"{acc.account_name} ({acc.platform}) Error: {clean_msg}")
                failed_account_ids.append(acc.id)

        total_duration = round(time.time() - start_time, 2)

        # Determine overall outcome
        if successful_account_ids:
            story.status = StoryStatus.PUBLISHED.value
            story.published_at = datetime.now(timezone.utc)
            if errors:
                story.last_error = f"Published with warnings: {' | '.join(errors)}"
            else:
                story.last_error = None
            db.commit()
            db.refresh(story)

            logger.info(
                f"[STORY_PUBLISH_COMPLETED] story_id={story.id} duration={total_duration}s status={story.status} "
                f"successful_account_ids={successful_account_ids} failed_account_ids={failed_account_ids} "
                f"fb_story_id={story.fb_story_id} ig_story_id={story.ig_story_id} "
                f"fb_story_url={story.fb_story_url} ig_story_url={story.ig_story_url} ig_username={story.ig_username}"
            )

            audit_repo.log(
                db=db,
                user_id=story.user_id,
                action="STORY_PUBLISHED",
                resource_type="Story",
                resource_id=story.id,
                details={
                    "target_account_ids": target_ids,
                    "successful_account_ids": successful_account_ids,
                    "failed_account_ids": failed_account_ids,
                    "successful_platforms": successful_platforms,
                    "errors": errors,
                    "duration_seconds": total_duration
                }
            )
            return story
        else:
            story.status = StoryStatus.FAILED.value
            story.retry_count += 1
            story.last_error = " | ".join(errors) if errors else "Story publishing failed for all targeted accounts."
            db.commit()
            db.refresh(story)

            logger.error(
                f"[STORY_PUBLISH_FAILED] story_id={story.id} duration={total_duration}s status={story.status} "
                f"successful_account_ids={successful_account_ids} failed_account_ids={failed_account_ids} "
                f"errors={errors}"
            )

            audit_repo.log(
                db=db,
                user_id=story.user_id,
                action="STORY_PUBLISH_FAILED",
                resource_type="Story",
                resource_id=story.id,
                details={
                    "target_account_ids": target_ids,
                    "successful_account_ids": successful_account_ids,
                    "failed_account_ids": failed_account_ids,
                    "errors": errors,
                    "retry_count": story.retry_count,
                    "duration_seconds": total_duration
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Story publishing failed: {story.last_error}"
            )

    def retry_story(self, db: Session, story_id: int, user_id: int) -> Story:
        """Retry a failed story."""
        story = self.get_story(db, story_id, user_id)
        if story.status != StoryStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only failed stories can be retried. Current status: '{story.status}'."
            )
        if story.retry_count >= story.max_retries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum retries ({story.max_retries}) exceeded for Story ID {story_id}."
            )
        return self.publish_story(db, story_id, user_id)

    def check_and_publish_due_stories(self, db: Session, user_id: Optional[int] = None) -> List[Story]:
        """Find scheduled stories whose time has passed and publish them."""
        now = datetime.now(timezone.utc)
        due_stories = story_repo.get_due_scheduled_stories(db, now)
        if user_id:
            due_stories = [s for s in due_stories if s.user_id == user_id]

        published_stories: List[Story] = []
        for s in due_stories:
            try:
                pub = self.publish_story(db, s.id, s.user_id)
                published_stories.append(pub)
            except Exception as e:
                logger.error(f"[STORY_SCHEDULER] Error auto-publishing due story {s.id}: {e}")

        return published_stories


story_service = StoryService()
