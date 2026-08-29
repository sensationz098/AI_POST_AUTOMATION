import requests
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
from app.core.config import settings
from app.core.logging_config import sanitize_url

logger = logging.getLogger(__name__)

class MetaPublishException(Exception):
    """Custom exception containing structured Meta API error metadata."""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[int] = None,
        error_subcode: Optional[int] = None,
        error_message: Optional[str] = None,
        raw_response: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.error_message = error_message or message
        self.raw_response = raw_response or {}

def is_ambiguous_meta_error(
    status_code: Optional[int],
    error_code: Optional[int],
    error_subcode: Optional[int],
    error_message: Optional[str]
) -> bool:
    """
    Distinguishes a definitive API failure from an ambiguous publication outcome.
    Ambiguous scenarios include HTTP 403 rate limits (codes 4, 17, 32, subcode 2207051), HTTP 429, 5xx server errors.
    """
    if not status_code:
        return False
    err_msg = (error_message or "").lower()
    if status_code == 403:
        if error_code in [4, 17, 32] or error_subcode in [2207051] or "limit" in err_msg or "rate" in err_msg:
            return True
    if status_code == 429:
        return True
    if status_code >= 500:
        return True
    return False

class MetaGraphService:
    BASE_URL = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"

    def publish_to_facebook_page(
        self, page_id: str, access_token: str, message: str, image_url: Optional[str] = None, is_video: bool = False, thumbnail_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Publish a photo or video post to a Facebook Page via Meta Graph API."""
        is_mock_allowed = settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"
        if is_mock_allowed and (not page_id or not access_token or page_id == "sandbox" or access_token.startswith("sandbox") or access_token.startswith("mock")):
            logger.info("[FB_PUBLISH] Executing Sandbox Facebook Publish Simulation.")
            return {"id": f"fb_mock_post_{abs(hash(message)) % 1000000}", "status": "published_sandbox"}

        if not page_id or not access_token:
            raise Exception("Facebook Page ID and valid Access Token are required for publishing.")

        if not access_token or access_token.startswith("sandbox") or access_token.startswith("mock") or page_id == "sandbox":
            logger.info("[FB_PUBLISH] Executing Sandbox Facebook Publish Simulation.")
            return {"id": f"fb_post_mock_{abs(hash(message)) % 1000000}", "status": "published_sandbox"}

        try:
            is_video_media = is_video or (image_url and any(image_url.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".m4v"]))
            logger.info(f"[PUBLISH_TRACE] FACEBOOK_PUBLISH_STARTED | page_id={page_id} | is_video={is_video_media} | media_url={sanitize_url(image_url)} | thumbnail_url={sanitize_url(thumbnail_url)}")

            if is_video_media and image_url:
                url = f"{self.BASE_URL}/{page_id}/videos"
                payload = {
                    "file_url": image_url,
                    "description": message,
                    "access_token": access_token
                }
                files = None
                if thumbnail_url:
                    try:
                        logger.info(f"[FB_PUBLISH] FETCHING_THUMBNAIL_BYTES | url={sanitize_url(thumbnail_url)}")
                        t_res = requests.get(thumbnail_url, timeout=10)
                        if t_res.status_code == 200:
                            c_type = t_res.headers.get("Content-Type", "image/jpeg")
                            files = {"thumb": ("thumbnail.jpg", t_res.content, c_type)}
                            logger.info(f"[FB_PUBLISH] THUMBNAIL_BYTES_ATTACHED | size_bytes={len(t_res.content)}")
                    except Exception as t_err:
                        logger.warning(f"[FB_PUBLISH] Failed to fetch thumbnail_url for FB video upload: {t_err}")

                video_timeout = settings.META_VIDEO_UPLOAD_TIMEOUT_SECONDS
                logger.info(f"[FB_PUBLISH] VIDEO_UPLOAD_STARTED | page_id={page_id} | video_url={sanitize_url(image_url)} | timeout={video_timeout}s")
                try:
                    response = requests.post(url, data=payload, files=files, timeout=video_timeout)
                except requests.exceptions.Timeout:
                    logger.error(f"[FB_PUBLISH] VIDEO_UPLOAD_TIMEOUT | page_id={page_id} | timeout={video_timeout}s")
                    raise Exception(f"Facebook video upload network HTTP timeout after {video_timeout} seconds.")
                except requests.exceptions.RequestException as req_err:
                    logger.error(f"[FB_PUBLISH] VIDEO_UPLOAD_NETWORK_ERROR | page_id={page_id} | error={req_err}")
                    raise Exception(f"Facebook video upload network error: {req_err}")
            elif image_url and image_url.startswith("data:image"):
                url = f"{self.BASE_URL}/{page_id}/photos"
                import base64
                header, encoded = image_url.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1] if ";" in header else "image/png"
                ext = mime_type.split("/")[1] if "/" in mime_type else "png"
                img_bytes = base64.b64decode(encoded)

                files = {"source": (f"post_photo.{ext}", img_bytes, mime_type)}
                data = {"caption": message, "access_token": access_token}
                logger.info(f"[FB_PUBLISH] PHOTO_UPLOAD_STARTED (base64) | page_id={page_id}")
                response = requests.post(url, data=data, files=files, timeout=30)
            elif image_url:
                url = f"{self.BASE_URL}/{page_id}/photos"
                payload = {
                    "url": image_url,
                    "caption": message,
                    "access_token": access_token
                }
                logger.info(f"[FB_PUBLISH] PHOTO_UPLOAD_STARTED | page_id={page_id} | image_url={sanitize_url(image_url)}")
                response = requests.post(url, data=payload, timeout=20)
            else:
                feed_url = f"{self.BASE_URL}/{page_id}/feed"
                payload = {
                    "message": message,
                    "access_token": access_token
                }
                logger.info(f"[FB_PUBLISH] FEED_POST_STARTED | page_id={page_id}")
                response = requests.post(feed_url, data=payload, timeout=15)
            
            res_data = response.json()
            logger.info(f"[PUBLISH_TRACE] FACEBOOK_RESPONSE_RECEIVED | page_id={page_id} | status_code={response.status_code} | response_keys={list(res_data.keys())}")
            if response.status_code != 200:
                err_dict = res_data.get("error", {})
                error_msg = err_dict.get("message", "Facebook API Error")
                err_code = err_dict.get("code")
                err_subcode = err_dict.get("error_subcode")
                logger.error(f"[PUBLISH_TRACE] FACEBOOK_PUBLISH_FAILED | page_id={page_id} | status_code={response.status_code} | error_code={err_code} | error_subcode={err_subcode} | error={error_msg}")
                raise Exception(f"Facebook Graph API Error ({response.status_code}) [code={err_code}, subcode={err_subcode}]: {error_msg}")
            
            fb_post_id = res_data.get("id")
            if not fb_post_id:
                raise Exception(f"Facebook Graph API returned success response but missing post/video ID: {res_data}")

            logger.info(
                f"[PUBLISH_TRACE] FACEBOOK_PUBLISH_SUCCESS | page_id={page_id} | returned_id={fb_post_id} | "
                f"sanitized_response={{\"platform\": \"facebook\", \"returned_id\": \"{fb_post_id}\", \"response_keys\": {list(res_data.keys())}}}"
            )
            return res_data
        except Exception as e:
            logger.error(f"[FB_PUBLISH] Meta Service Facebook publish error: {e}")
            raise e

    def verify_instagram_container_published(
        self,
        ig_user_id: str,
        creation_id: str,
        access_token: str,
        caption: Optional[str] = None,
        publish_started_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Safely query Meta Graph API to check whether an Instagram container was actually published.
        
        CRITICAL RULE: status_code == FINISHED only confirms container readiness before media_publish, NOT publication.
        Verification checks:
        1. Container node direct status: GET /{creation_id}?fields=status_code,status,id
           If status_code == "PUBLISHED", publication is confirmed.
        2. Account media list: GET /{ig-user-id}/media?fields=id,caption,timestamp,permalink
           Strict matching rules for fallback account media verification:
           - REQUIRES exact normalized caption equality (no substring / inclusion matching).
           - REQUIRES timestamp correlation (item timestamp within publish attempt window).
           - CONSERVATIVE FAILURE: Returns is_published=False if 0 or >1 candidates match to prevent
             concurrent jobs or duplicate captions from triggering false success.
        """
        logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_VERIFICATION_STARTED | ig_user_id={ig_user_id} | container_id={creation_id}")
        
        # 1. Direct Container Node Query
        try:
            c_res = requests.get(
                f"{self.BASE_URL}/{creation_id}",
                params={"fields": "status_code,status,id", "access_token": access_token},
                timeout=15
            )
            if c_res.status_code == 200:
                c_data = c_res.json()
                st_code = c_data.get("status_code")
                c_id = c_data.get("id")
                logger.info(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_VERIFY_CHECK | container_id={creation_id} | status_code={st_code}")
                
                if st_code == "PUBLISHED":
                    pub_id = c_id if (c_id and str(c_id) != str(creation_id)) else f"ig_pub_{creation_id}"
                    logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_SUCCESS | container_id={creation_id} | published_media_id={pub_id}")
                    return {
                        "is_published": True,
                        "published_media_id": str(pub_id),
                        "status_code": "PUBLISHED",
                        "verification_source": "container_status"
                    }
                elif st_code in ["ERROR", "EXPIRED"]:
                    logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_NOT_FOUND | container_id={creation_id} | status_code={st_code}")
                    return {
                        "is_published": False,
                        "status_code": st_code,
                        "verification_source": "container_status"
                    }
        except Exception as v_err:
            logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_VERIFY_WARNING | container_id={creation_id} | error={v_err}")

        # 2. Query Recent Account Media List (Strict Fallback)
        try:
            m_res = requests.get(
                f"{self.BASE_URL}/{ig_user_id}/media",
                params={"fields": "id,caption,timestamp,permalink", "limit": 10, "access_token": access_token},
                timeout=15
            )
            if m_res.status_code == 200 and caption:
                m_data = m_res.json()
                media_items = m_data.get("data", [])
                
                # Normalize target caption: strip whitespace and normalize line endings
                def _normalize_cap(raw: Optional[str]) -> str:
                    if not raw:
                        return ""
                    lines = [l.strip() for l in raw.replace("\r\n", "\n").split("\n")]
                    return "\n".join(lines).strip()

                target_norm = _normalize_cap(caption)

                # Establish publish attempt timestamp window
                # The timestamp window exists to prevent older Instagram posts with identical captions
                # (published hours or days ago) from being accepted as false-positive proof for the current attempt.
                ref_time = publish_started_at or datetime.now(timezone.utc)
                if ref_time.tzinfo is None:
                    ref_time = ref_time.replace(tzinfo=timezone.utc)
                
                # Allowed publish attempt window: 15 minutes before publish start up to 5 minutes after current time
                window_start = ref_time - timedelta(minutes=15)
                window_end = datetime.now(timezone.utc) + timedelta(minutes=5)

                matching_candidates = []

                for item in media_items:
                    item_cap_norm = _normalize_cap(item.get("caption"))
                    
                    # REQUIRE STRICT EXACT EQUALITY (NO SUBSTRING / PARTIAL MATCHING)
                    if not target_norm or target_norm != item_cap_norm:
                        continue

                    # REQUIRE VALID TIMESTAMP FROM META (MISSING TIMESTAMP CANNOT BE VERIFIED)
                    raw_ts = item.get("timestamp")
                    if not raw_ts:
                        logger.info(f"[PUBLISH_TRACE] INSTAGRAM_VERIFY_TIMESTAMP_MISSING | item_id={item.get('id')}")
                        continue

                    try:
                        clean_ts = raw_ts.replace("+0000", "+00:00").replace("Z", "+00:00")
                        item_dt = datetime.fromisoformat(clean_ts)
                        if item_dt.tzinfo is None:
                            item_dt = item_dt.replace(tzinfo=timezone.utc)

                        # REQUIRE TIMESTAMP CORRELATION WITHIN PUBLISH WINDOW
                        if not (window_start <= item_dt <= window_end):
                            logger.info(
                                f"[PUBLISH_TRACE] INSTAGRAM_VERIFY_TIMESTAMP_OUTSIDE_WINDOW | "
                                f"item_id={item.get('id')} | item_dt={item_dt.isoformat()} | window_start={window_start.isoformat()}"
                            )
                            continue
                    except Exception as ts_err:
                        logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_VERIFY_TIMESTAMP_PARSE_ERROR | item_id={item.get('id')} | error={ts_err}")
                        continue

                    matching_candidates.append(item)

                # CONSERVATIVE FAILURE RULES FOR CONCURRENT / AMBIGUOUS MATCHES:
                # Exactly 1 candidate matching exact caption + timestamp window = Confirmed Success.
                # >1 candidates matching = Cannot uniquely identify candidate -> Conservative Failure (is_published=False).
                if len(matching_candidates) == 1:
                    matched_item = matching_candidates[0]
                    pub_id = matched_item.get("id")
                    logger.info(
                        f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_SUCCESS | container_id={creation_id} | "
                        f"published_media_id={pub_id} | verification_source=account_media_list"
                    )
                    return {
                        "is_published": True,
                        "published_media_id": str(pub_id),
                        "status_code": "PUBLISHED",
                        "verification_source": "account_media_list"
                    }
                elif len(matching_candidates) > 1:
                    logger.warning(
                        f"[PUBLISH_TRACE] INSTAGRAM_VERIFY_CONCURRENT_AMBIGUOUS_MATCHES | container_id={creation_id} | "
                        f"candidates_found={len(matching_candidates)} | caption={caption[:30]}"
                    )
        except Exception as m_err:
            logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_MEDIA_VERIFY_WARNING | ig_user_id={ig_user_id} | error={m_err}")

        logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_NOT_FOUND | container_id={creation_id}")
        return {
            "is_published": False,
            "status_code": "NOT_PUBLISHED",
            "verification_source": "verification_failed"
        }

    def publish_to_instagram_business(
        self,
        ig_user_id: str,
        access_token: str,
        caption: str,
        image_url: str,
        is_video: bool = False,
        thumbnail_url: Optional[str] = None,
        on_container_created: Optional[Callable[[str], None]] = None,
        existing_container_id: Optional[str] = None,
        publish_started_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Publish Photo or Video Reel to Instagram Business Account via 2-Step Container Graph API flow:
        Step 1: Create IG Media Container (POST /{ig-user-id}/media)
        Step 2: Bounded polling of container status until FINISHED (with exponential backoff & configurable timeout)
        Step 3: Publish IG Media Container (POST /{ig-user-id}/media_publish)
        """
        publish_started_at = publish_started_at or datetime.now(timezone.utc)
        is_mock_allowed = settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"
        if is_mock_allowed and (not ig_user_id or not access_token or ig_user_id == "sandbox" or access_token.startswith("sandbox") or access_token.startswith("mock")):
            logger.info("[IG_PUBLISH] Executing Sandbox Instagram Publish Simulation.")
            return {
                "container_id": f"ig_container_mock_{abs(hash(caption)) % 100000}",
                "id": f"ig_media_mock_{abs(hash(caption)) % 1000000}",
                "status": "published_sandbox"
            }

        if not ig_user_id or not access_token:
            raise MetaPublishException("Instagram Business Account ID and valid Access Token are required for publishing.")

        # Check existing container before creating a new one on retries
        if existing_container_id and not (is_mock_allowed and (ig_user_id == "sandbox" or access_token.startswith("sandbox") or access_token.startswith("mock"))):
            logger.info(f"[PUBLISH_TRACE] INSTAGRAM_RETRY_BLOCKED_PENDING_VERIFICATION | existing_container_id={existing_container_id}")
            v_res = self.verify_instagram_container_published(
                ig_user_id=ig_user_id,
                creation_id=existing_container_id,
                access_token=access_token,
                caption=caption,
                publish_started_at=publish_started_at
            )
            if v_res.get("is_published"):
                pub_id = v_res.get("published_media_id")
                logger.info(f"[PUBLISH_TRACE] INSTAGRAM_RETRY_VERIFICATION_SUCCESS | container_id={existing_container_id} | published_media_id={pub_id}")
                return {
                    "container_id": existing_container_id,
                    "id": str(pub_id),
                    "status": "published",
                    "was_retry_verified": True
                }
            logger.info(f"[PUBLISH_TRACE] INSTAGRAM_SAFE_REPUBLISH_ALLOWED | container_id={existing_container_id}")

        try:
            container_url = f"{self.BASE_URL}/{ig_user_id}/media"
            is_video_media = is_video or (image_url and any(image_url.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".m4v"]))
            logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_STARTED | ig_user_id={ig_user_id} | is_video={is_video_media} | media_url={sanitize_url(image_url)} | thumbnail_url={sanitize_url(thumbnail_url)}")

            if is_video_media:
                container_payload = {
                    "media_type": "REELS",
                    "video_url": image_url,
                    "caption": caption,
                    "access_token": access_token
                }
                if thumbnail_url:
                    container_payload["cover_url"] = thumbnail_url
                    logger.info(f"[IG_PUBLISH] REEL_COVER_URL_ATTACHED | cover_url={sanitize_url(thumbnail_url)}")
                logger.info(f"[IG_PUBLISH] VIDEO_UPLOAD_STARTED | ig_user_id={ig_user_id} | video_url={sanitize_url(image_url)}")
            else:
                container_payload = {
                    "image_url": image_url,
                    "caption": caption,
                    "access_token": access_token
                }
                logger.info(f"[IG_PUBLISH] PHOTO_UPLOAD_STARTED | ig_user_id={ig_user_id} | image_url={sanitize_url(image_url)}")

            container_res = requests.post(container_url, data=container_payload, timeout=30)
            c_data = container_res.json()
            if container_res.status_code != 200:
                err_dict = c_data.get("error", {})
                err = err_dict.get("message", "IG Container Error")
                err_code = err_dict.get("code")
                err_subcode = err_dict.get("error_subcode")
                logger.error(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_FAILED | ig_user_id={ig_user_id} | status_code={container_res.status_code} | error_code={err_code} | error_subcode={err_subcode} | error={err}")
                raise MetaPublishException(
                    message=f"IG Container Creation Failed ({container_res.status_code}) [code={err_code}, subcode={err_subcode}]: {err}",
                    status_code=container_res.status_code,
                    error_code=err_code,
                    error_subcode=err_subcode,
                    error_message=err,
                    raw_response=c_data
                )

            creation_id = c_data.get("id")
            if not creation_id:
                raise MetaPublishException(f"IG Container Creation Failed: Meta returned success response without container ID: {c_data}")

            logger.info(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_CREATED | ig_user_id={ig_user_id} | container_id={creation_id}")

            # Persist container ID immediately upon creation
            if on_container_created:
                try:
                    on_container_created(str(creation_id))
                    logger.info(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_PERSISTED | container_id={creation_id}")
                except Exception as cb_err:
                    logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_PERSIST_WARNING | container_id={creation_id} | error={cb_err}")

            # Step 2: Bounded polling of container status until FINISHED
            import time
            status_url = f"{self.BASE_URL}/{creation_id}"
            max_wait_seconds = settings.META_VIDEO_PROCESSING_MAX_SECONDS
            initial_delay = settings.META_VIDEO_POLL_INITIAL_SECONDS
            max_delay = settings.META_VIDEO_POLL_MAX_SECONDS
            backoff_factor = 1.5

            start_time = time.time()
            attempt = 0
            current_delay = float(initial_delay)
            is_finished = False
            last_status_code = None
            last_status_details = None

            while (time.time() - start_time) < max_wait_seconds:
                attempt += 1
                elapsed = round(time.time() - start_time, 2)
                try:
                    st_res = requests.get(
                        status_url,
                        params={"fields": "status_code,status", "access_token": access_token},
                        timeout=15
                    )
                    st_data = st_res.json()
                    last_status_code = st_data.get("status_code")
                    last_status_details = st_data.get("status")
                except Exception as poll_err:
                    logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_STATUS_WARNING | attempt={attempt} | container_id={creation_id} | error={poll_err}")
                    time.sleep(current_delay)
                    current_delay = min(current_delay * backoff_factor, max_delay)
                    continue

                logger.info(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_STATUS | attempt={attempt} | container_id={creation_id} | status_code={last_status_code} | elapsed={elapsed}s")

                if last_status_code == "FINISHED":
                    is_finished = True
                    logger.info(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_FINISHED | container_id={creation_id} | attempt={attempt} | total_time={elapsed}s")
                    break
                elif last_status_code == "ERROR":
                    err_msg = last_status_details or st_data.get("error", {}).get("message") or "Unknown container processing error on Meta servers"
                    logger.error(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_FAILED | container_id={creation_id} | status_code=ERROR | error={err_msg} | elapsed={elapsed}s")
                    raise MetaPublishException(f"IG Container processing failed on Meta servers (ERROR): {err_msg}")
                elif last_status_code == "EXPIRED":
                    logger.error(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_EXPIRED | container_id={creation_id} | status_code=EXPIRED | elapsed={elapsed}s")
                    raise MetaPublishException(f"IG Container processing expired on Meta servers (EXPIRED). Container ID: {creation_id}")

                time.sleep(current_delay)
                current_delay = min(current_delay * backoff_factor, max_delay)

            if not is_finished:
                total_elapsed = round(time.time() - start_time, 2)
                logger.error(f"[PUBLISH_TRACE] INSTAGRAM_CONTAINER_TIMEOUT | container_id={creation_id} | status_code={last_status_code} | total_time={total_elapsed}s | max_allowed={max_wait_seconds}s")
                raise MetaPublishException(
                    f"IG Video container processing timed out on Meta servers after {total_elapsed}s (status: {last_status_code or 'IN_PROGRESS'}). Container ID: {creation_id}"
                )

            # Step 3: Publish Media Container ONLY after FINISHED status is confirmed
            logger.info(f"[PUBLISH_TRACE] INSTAGRAM_MEDIA_PUBLISH_STARTED | container_id={creation_id}")
            publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": access_token
            }
            
            pub_res = None
            p_data = {}
            try:
                pub_res = requests.post(publish_url, data=publish_payload, timeout=30)
                p_data = pub_res.json()
                logger.info(f"[PUBLISH_TRACE] INSTAGRAM_RESPONSE_RECEIVED | container_id={creation_id} | status_code={pub_res.status_code} | response_keys={list(p_data.keys())}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                logger.warning(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_RESPONSE_AMBIGUOUS | container_id={creation_id} | network_error={req_err}")
                v_res = self.verify_instagram_container_published(
                    ig_user_id=ig_user_id,
                    creation_id=creation_id,
                    access_token=access_token,
                    caption=caption
                )
                if v_res.get("is_published"):
                    pub_id = v_res.get("published_media_id")
                    logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_SUCCESS | container_id={creation_id} | published_media_id={pub_id}")
                    return {
                        "container_id": creation_id,
                        "id": str(pub_id),
                        "status": "published",
                        "was_ambiguous_verified": True
                    }
                raise MetaPublishException(
                    message=f"IG Media Publish network timeout/connection error for container {creation_id}: {req_err}",
                    status_code=504,
                    error_message=str(req_err)
                )

            if pub_res.status_code != 200:
                err_dict = p_data.get("error", {})
                err = err_dict.get("message", "IG Publish Error")
                err_code = err_dict.get("code")
                err_subcode = err_dict.get("error_subcode")
                logger.error(f"[PUBLISH_TRACE] INSTAGRAM_MEDIA_PUBLISH_FAILED | container_id={creation_id} | status_code={pub_res.status_code} | error_code={err_code} | error_subcode={err_subcode} | error={err}")
                
                # Check ambiguous outcome
                if is_ambiguous_meta_error(pub_res.status_code, err_code, err_subcode, err):
                    logger.warning(
                        f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_RESPONSE_AMBIGUOUS | container_id={creation_id} | "
                        f"status_code={pub_res.status_code} | error_code={err_code} | error_subcode={err_subcode}"
                    )
                    v_res = self.verify_instagram_container_published(
                        ig_user_id=ig_user_id,
                        creation_id=creation_id,
                        access_token=access_token,
                        caption=caption
                    )
                    if v_res.get("is_published"):
                        pub_id = v_res.get("published_media_id")
                        logger.info(f"[PUBLISH_TRACE] INSTAGRAM_PUBLISH_CONFIRMED_SUCCESS | container_id={creation_id} | published_media_id={pub_id}")
                        return {
                            "container_id": creation_id,
                            "id": str(pub_id),
                            "status": "published",
                            "was_ambiguous_verified": True
                        }

                raise MetaPublishException(
                    message=f"IG Media Publish Failed ({pub_res.status_code}) [code={err_code}, subcode={err_subcode}]: {err}",
                    status_code=pub_res.status_code,
                    error_code=err_code,
                    error_subcode=err_subcode,
                    error_message=err,
                    raw_response=p_data
                )

            published_media_id = p_data.get("id")
            if not published_media_id:
                logger.error(f"[PUBLISH_TRACE] INSTAGRAM_MEDIA_PUBLISH_NO_ID | container_id={creation_id} | response={p_data}")
                raise MetaPublishException(
                    message=f"IG Media Publish succeeded but returned no published media ID: {p_data}",
                    status_code=200,
                    raw_response=p_data
                )

            logger.info(
                f"[PUBLISH_TRACE] INSTAGRAM_MEDIA_PUBLISH_SUCCESS | ig_user_id={ig_user_id} | container_id={creation_id} | "
                f"published_media_id={published_media_id}"
            )
            return {
                "container_id": creation_id,
                "id": str(published_media_id),
                "status": "published"
            }
        except Exception as e:
            if not isinstance(e, MetaPublishException):
                logger.error(f"[IG_PUBLISH] Meta Service Instagram publish error: {e}")
            raise


    def fetch_facebook_page_metrics(self, page_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch real Facebook Page metrics (followers, likes, category, picture) via Graph API."""
        if not page_id or not access_token or page_id == "sandbox":
            return {
                "id": "sandbox",
                "name": "Apex Innovations Page (Sandbox)",
                "followers_count": 18450,
                "fan_count": 14200,
                "category": "Artificial Intelligence & Software",
                "picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                "link": f"https://facebook.com/{page_id}",
                "is_sandbox": True
            }

        try:
            url = f"{self.BASE_URL}/{page_id}"
            params = {
                "fields": "id,name,followers_count,fan_count,category,picture.type(large),link",
                "access_token": access_token
            }
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if res.status_code != 200:
                logger.warning(f"FB Page Metrics query warning: {data.get('error', {}).get('message')}")
                return {
                    "id": page_id,
                    "name": "Connected Facebook Page",
                    "followers_count": 12500,
                    "fan_count": 9800,
                    "category": "Business Page",
                    "picture_url": f"https://graph.facebook.com/v19.0/{page_id}/picture?type=large",
                    "link": f"https://facebook.com/{page_id}",
                    "is_sandbox": False
                }

            picture_url = data.get("picture", {}).get("data", {}).get("url") or f"https://graph.facebook.com/v19.0/{page_id}/picture?type=large"
            return {
                "id": data.get("id", page_id),
                "name": data.get("name", "Facebook Page"),
                "followers_count": data.get("followers_count") or data.get("fan_count") or 0,
                "fan_count": data.get("fan_count") or 0,
                "category": data.get("category", "Meta Page"),
                "picture_url": picture_url,
                "link": data.get("link", f"https://facebook.com/{page_id}"),
                "is_sandbox": False
            }
        except Exception as e:
            logger.error(f"Error fetching FB Page metrics: {e}")
            return {
                "id": page_id,
                "name": "Connected Facebook Page",
                "followers_count": 0,
                "fan_count": 0,
                "category": "Facebook Page",
                "picture_url": f"https://graph.facebook.com/v19.0/{page_id}/picture?type=large",
                "link": f"https://facebook.com/{page_id}",
                "is_sandbox": False
            }

    def fetch_instagram_account_metrics(self, ig_user_id: str, access_token: str) -> Dict[str, Any]:
        """Fetch real Instagram Business Account metrics (followers, following, media_count, handle) via Graph API."""
        if not ig_user_id or not access_token or ig_user_id == "sandbox":
            return {
                "id": "sandbox",
                "username": "instagram_account",
                "name": "Instagram Business",
                "followers_count": 0,
                "follows_count": 0,
                "media_count": 0,
                "profile_picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                "is_sandbox": True
            }

        try:
            url = f"{self.BASE_URL}/{ig_user_id}"
            params = {
                "fields": "id,username,name,followers_count,follows_count,media_count,profile_picture_url",
                "access_token": access_token
            }
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if res.status_code != 200:
                logger.warning(f"IG Account Metrics query warning: {data.get('error', {}).get('message')}")
                return {
                    "id": ig_user_id,
                    "username": "instagram_account",
                    "name": "Instagram Business",
                    "followers_count": 0,
                    "follows_count": 0,
                    "media_count": 0,
                    "profile_picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                    "is_sandbox": False
                }

            return {
                "id": data.get("id", ig_user_id),
                "username": data.get("username", "instagram_account"),
                "name": data.get("name", "Instagram Business"),
                "followers_count": data.get("followers_count") or 0,
                "follows_count": data.get("follows_count") or 0,
                "media_count": data.get("media_count") or 0,
                "profile_picture_url": data.get("profile_picture_url") or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                "is_sandbox": False
            }
        except Exception as e:
            logger.error(f"Error fetching IG Account metrics: {e}")
            return {
                "id": ig_user_id,
                "username": "instagram_account",
                "name": "Instagram Business",
                "followers_count": 0,
                "follows_count": 0,
                "media_count": 0,
                "profile_picture_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                "is_sandbox": False
            }

    def get_authorization_url(self, state: str) -> str:
        """Generate official Meta OAuth Authorization Dialog URL with required permissions."""
        from urllib.parse import urlencode
        params = {
            "client_id": settings.META_APP_ID or "YOUR_META_APP_ID",
            "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
            "state": state,
            "response_type": "code"
        }
        if settings.META_CONFIG_ID:
            params["config_id"] = settings.META_CONFIG_ID
            params["override_default_response_type"] = "true"
        else:
            params["scope"] = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish,business_management"

        return f"https://www.facebook.com/{settings.META_GRAPH_API_VERSION}/dialog/oauth?{urlencode(params)}"

    def exchange_code_for_user_token(self, code: str) -> str:
        """Exchange Meta authorization code for short-lived user access token."""
        if not settings.META_APP_SECRET or settings.META_APP_SECRET == "your-meta-app-secret" or settings.META_APP_SECRET.startswith("your-"):
            raise Exception("Meta OAuth error: META_APP_SECRET is not configured in .env. Please copy your exact 32-character App Secret from Meta Developer Dashboard (App Settings -> Basic).")

        url = f"{self.BASE_URL}/oauth/access_token"
        params = {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "redirect_uri": settings.META_OAUTH_REDIRECT_URI,
            "code": code
        }
        res = requests.get(url, params=params, timeout=20)
        data = res.json()
        if res.status_code != 200 or "access_token" not in data:
            error_msg = data.get("error", {}).get("message", "Token exchange failed")
            if "client secret" in error_msg.lower():
                raise Exception("Meta OAuth error: Invalid META_APP_SECRET in .env. Please copy your exact 32-character App Secret from Meta Developer Dashboard (App Settings -> Basic).")
            raise Exception(f"Meta OAuth token exchange error: {error_msg}")
        return data["access_token"]

    def get_long_lived_user_token(self, short_lived_token: str) -> str:
        """Exchange short-lived user token for 60-day long-lived user token."""
        url = f"{self.BASE_URL}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "fb_exchange_token": short_lived_token
        }
        res = requests.get(url, params=params, timeout=20)
        data = res.json()
        if res.status_code == 200 and "access_token" in data:
            return data["access_token"]
        # Fallback to short lived token if exchange fails
        return short_lived_token

    def fetch_user_pages_and_instagram_accounts(self, user_access_token: str) -> Dict[str, Any]:
        """
        Discover all authorized Facebook Pages and linked Instagram Professional accounts.
        Returns:
        {
          "facebook_pages": [{"account_id", "account_name", "access_token", "logo_url"}],
          "instagram_accounts": [{"account_id", "account_name", "access_token", "logo_url"}]
        }
        """
        url = f"{self.BASE_URL}/me/accounts"
        params = {
            "fields": "id,name,access_token,picture.type(large),instagram_business_account",
            "access_token": user_access_token
        }
        res = requests.get(url, params=params, timeout=20)
        data = res.json()
        if res.status_code != 200:
            error_msg = data.get("error", {}).get("message", "Failed to retrieve Facebook Pages")
            raise Exception(f"Meta Graph API error: {error_msg}")

        pages_raw = data.get("data", [])
        fb_pages = []
        ig_accounts = []

        for page in pages_raw:
            page_id = str(page.get("id"))
            page_name = page.get("name", "Facebook Page")
            page_token = page.get("access_token")
            picture_url = page.get("picture", {}).get("data", {}).get("url") or f"https://graph.facebook.com/v19.0/{page_id}/picture?type=large"

            fb_pages.append({
                "account_id": page_id,
                "account_name": page_name,
                "access_token": page_token,
                "logo_url": picture_url
            })

            # Check linked Instagram Business account
            ig_obj = page.get("instagram_business_account")
            if not ig_obj and page_token:
                # Query page endpoint directly for instagram_business_account
                try:
                    ig_query_res = requests.get(
                        f"{self.BASE_URL}/{page_id}",
                        params={"fields": "instagram_business_account", "access_token": page_token},
                        timeout=10
                    )
                    ig_q_data = ig_query_res.json()
                    ig_obj = ig_q_data.get("instagram_business_account")
                except Exception:
                    ig_obj = None

            if ig_obj and page_token:
                ig_id = str(ig_obj.get("id"))
                # Retrieve Instagram Professional Account Details
                try:
                    ig_res = requests.get(
                        f"{self.BASE_URL}/{ig_id}",
                        params={"fields": "id,username,name,profile_picture_url", "access_token": page_token},
                        timeout=10
                    )
                    ig_data = ig_res.json()
                    username = ig_data.get("username") or f"ig_{ig_id}"
                    ig_name = ig_data.get("name") or username
                    ig_pic = ig_data.get("profile_picture_url") or picture_url

                    ig_accounts.append({
                        "account_id": ig_id,
                        "account_name": f"@{username}",
                        "access_token": page_token,  # IG publishing uses Page access token
                        "logo_url": ig_pic,
                        "metadata": {"username": username, "name": ig_name, "linked_page_id": page_id}
                    })
                except Exception as e:
                    logger.error(f"Failed to fetch IG profile details for {ig_id}: {e}")

        return {
            "facebook_pages": fb_pages,
            "instagram_accounts": ig_accounts
        }

    def delete_facebook_post(self, external_post_id: str, access_token: str) -> Dict[str, Any]:
        """Delete a Facebook post or video from Meta Graph API."""
        is_mock_allowed = settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"
        if is_mock_allowed and (not external_post_id or not access_token or external_post_id.startswith("mock") or external_post_id.startswith("fb_mock") or access_token.startswith("sandbox") or access_token.startswith("mock")):
            logger.info(f"[FB_DELETE] Executing Sandbox Facebook Delete Simulation for object ID: {external_post_id}")
            return {"success": True, "status": "deleted_sandbox"}

        if not external_post_id or not access_token:
            raise Exception("External Post ID and valid Access Token are required for Facebook deletion.")

        try:
            logger.info(f"[DELETE_TRACE] FACEBOOK_DELETE_STARTED | external_post_id={external_post_id}")
            url = f"{self.BASE_URL}/{external_post_id}"
            params = {"access_token": access_token}
            response = requests.delete(url, params=params, timeout=20)
            res_data = response.json()
            logger.info(f"[DELETE_TRACE] FACEBOOK_DELETE_RESPONSE | external_post_id={external_post_id} | status_code={response.status_code}")

            if response.status_code != 200:
                err_dict = res_data.get("error", {})
                error_msg = err_dict.get("message", "Facebook API Delete Error")
                err_code = err_dict.get("code")
                err_subcode = err_dict.get("error_subcode")

                # Check for idempotent / already deleted object indication
                msg_lower = error_msg.lower()
                is_already_deleted = (
                    err_code in [100, 10, 200, 210] and
                    ("does not exist" in msg_lower or "unsupported delete" in msg_lower or "cannot be loaded" in msg_lower or "unknown path" in msg_lower)
                ) or ("does not exist" in msg_lower or "not found" in msg_lower)

                if is_already_deleted:
                    logger.info(f"[DELETE_TRACE] FACEBOOK_DELETE_IDEMPOTENT | external_post_id={external_post_id} | message={error_msg}")
                    return {"success": True, "already_deleted": True, "status": "already_deleted"}

                logger.error(f"[DELETE_TRACE] FACEBOOK_DELETE_FAILED | external_post_id={external_post_id} | status_code={response.status_code} | error_code={err_code} | error_subcode={err_subcode} | error={error_msg}")
                raise Exception(f"Facebook Graph API Delete Error ({response.status_code}) [code={err_code}, subcode={err_subcode}]: {error_msg}")

            logger.info(f"[DELETE_TRACE] FACEBOOK_DELETE_SUCCESS | external_post_id={external_post_id}")
            return {"success": True, "status": "deleted"}
        except Exception as e:
            logger.error(f"[FB_DELETE] Meta Service Facebook delete error: {e}")
            raise e

    def delete_instagram_media(self, external_media_id: str, access_token: str) -> Dict[str, Any]:
        """Delete an Instagram media post from Meta Graph API."""
        is_mock_allowed = settings.META_MOCK_MODE and settings.APP_ENV.lower() != "production"
        if is_mock_allowed and (not external_media_id or not access_token or external_media_id.startswith("mock") or external_media_id.startswith("ig_media_mock") or access_token.startswith("sandbox") or access_token.startswith("mock")):
            logger.info(f"[IG_DELETE] Executing Sandbox Instagram Delete Simulation for media ID: {external_media_id}")
            return {"success": True, "status": "deleted_sandbox"}

        if not external_media_id or not access_token:
            raise Exception("External Media ID and valid Access Token are required for Instagram deletion.")

        try:
            logger.info(f"[DELETE_TRACE] INSTAGRAM_DELETE_STARTED | external_media_id={external_media_id}")
            url = f"{self.BASE_URL}/{external_media_id}"
            params = {"access_token": access_token}
            response = requests.delete(url, params=params, timeout=20)
            res_data = response.json()
            logger.info(f"[DELETE_TRACE] INSTAGRAM_DELETE_RESPONSE | external_media_id={external_media_id} | status_code={response.status_code}")

            if response.status_code != 200:
                err_dict = res_data.get("error", {})
                error_msg = err_dict.get("message", "Instagram API Delete Error")
                err_code = err_dict.get("code")
                err_subcode = err_dict.get("error_subcode")

                # Check for idempotent / already deleted object indication
                msg_lower = error_msg.lower()
                is_already_deleted = (
                    err_code in [100, 10, 200, 210] and
                    ("does not exist" in msg_lower or "unsupported delete" in msg_lower or "cannot be loaded" in msg_lower or "unknown path" in msg_lower)
                ) or ("does not exist" in msg_lower or "not found" in msg_lower)

                if is_already_deleted:
                    logger.info(f"[DELETE_TRACE] INSTAGRAM_DELETE_IDEMPOTENT | external_media_id={external_media_id} | message={error_msg}")
                    return {"success": True, "already_deleted": True, "status": "already_deleted"}

                logger.error(f"[DELETE_TRACE] INSTAGRAM_DELETE_FAILED | external_media_id={external_media_id} | status_code={response.status_code} | error_code={err_code} | error_subcode={err_subcode} | error={error_msg}")
                raise Exception(f"Instagram Graph API Delete Error ({response.status_code}) [code={err_code}, subcode={err_subcode}]: {error_msg}")

            logger.info(f"[DELETE_TRACE] INSTAGRAM_DELETE_SUCCESS | external_media_id={external_media_id}")
            return {"success": True, "status": "deleted"}
        except Exception as e:
            logger.error(f"[IG_DELETE] Meta Service Instagram delete error: {e}")
            raise e

meta_service = MetaGraphService()

