import pytest
from unittest.mock import patch, MagicMock
from app.services.meta_service import meta_service, MetaPublishException, is_ambiguous_meta_error
from app.services.publisher_service import InstagramPublisher

def test_is_ambiguous_meta_error_helper():
    assert is_ambiguous_meta_error(403, 4, 2207051, "Application request limit reached") is True
    assert is_ambiguous_meta_error(429, 4, None, "Too many requests") is True
    assert is_ambiguous_meta_error(500, None, None, "Internal Server Error") is True
    assert is_ambiguous_meta_error(400, 100, None, "Invalid parameter") is False

def test_instagram_publish_ambiguous_error_published_verified_success():
    """Verify 403 Application request limit reached triggers verification, succeeds if post exists on IG."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # 1. Container creation response
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "180831187734431"}

        # 2. Container status FINISHED
        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.side_effect = [
            mock_status_res, # Status poll
            # Verification calls (if requests.get is used inside verify helper)
            MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"}),
            MagicMock(status_code=200, json=lambda: {"data": [{"id": "published_media_777", "caption": "Test Post"}]})
        ]

        # 3. Media publish response: 403 Rate Limit Error
        mock_publish_res = MagicMock(status_code=403)
        mock_publish_res.json.return_value = {
            "error": {
                "message": "Application request limit reached",
                "code": 4,
                "error_subcode": 2207051
            }
        }
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
            mock_verify.return_value = {
                "is_published": True,
                "published_media_id": "published_media_777",
                "verified_via": "user_media_list"
            }

            res = meta_service.publish_to_instagram_business(
                ig_user_id="17841400000000000",
                access_token="valid_token_123",
                caption="Test Post",
                image_url="https://example.com/image.jpg",
                is_video=False
            )

            assert res["container_id"] == "180831187734431"
            assert res["id"] == "published_media_777"
            assert res["status"] == "published"
            assert res.get("was_ambiguous_verified") is True
            mock_verify.assert_called_once()

def test_instagram_publish_ambiguous_error_not_published_raises_exception():
    """Verify 403 Application request limit reached raises exception if post is NOT verified on IG."""
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "180831187734431"}

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_status_res

        mock_publish_res = MagicMock(status_code=403)
        mock_publish_res.json.return_value = {
            "error": {
                "message": "Application request limit reached",
                "code": 4,
                "error_subcode": 2207051
            }
        }
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
            mock_verify.return_value = {"is_published": False}

            with pytest.raises(MetaPublishException) as exc_info:
                meta_service.publish_to_instagram_business(
                    ig_user_id="17841400000000000",
                    access_token="valid_token_123",
                    caption="Test Post",
                    image_url="https://example.com/image.jpg",
                    is_video=False
                )

            assert exc_info.value.status_code == 403
            assert exc_info.value.error_code == 4
            assert exc_info.value.error_subcode == 2207051

def test_instagram_publish_existing_container_reuse():
    """Verify passing existing_container_id uses verify_instagram_container_published to prevent duplicate creation."""
    with patch.object(meta_service, "verify_instagram_container_published") as mock_verify:
        mock_verify.return_value = {
            "is_published": True,
            "published_media_id": "media_reused_888",
            "verified_via": "user_media_list"
        }

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Reuse Container Test",
            image_url="https://example.com/image.jpg",
            is_video=False,
            existing_container_id="existing_container_999"
        )

        assert res["container_id"] == "existing_container_999"
        assert res["id"] == "media_reused_888"
        assert res["was_retry_verified"] is True
        mock_verify.assert_called_once()

def test_instagram_on_container_created_callback_invoked():
    """Verify on_container_created callback is invoked immediately upon creation."""
    callback_mock = MagicMock()

    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        mock_container_res = MagicMock(status_code=200)
        mock_container_res.json.return_value = {"id": "new_created_container_555"}

        mock_status_res = MagicMock(status_code=200)
        mock_status_res.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_status_res

        mock_publish_res = MagicMock(status_code=200)
        mock_publish_res.json.return_value = {"id": "published_media_555"}
        mock_post.side_effect = [mock_container_res, mock_publish_res]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token_123",
            caption="Callback Test",
            image_url="https://example.com/image.jpg",
            is_video=False,
            on_container_created=callback_mock
        )

        assert res["container_id"] == "new_created_container_555"
        callback_mock.assert_called_once_with("new_created_container_555")

# ---------------------------------------------------------------------------
# TARGETED VERIFICATION SAFETY TESTS (TEST 1 - TEST 6)
# ---------------------------------------------------------------------------
from datetime import datetime, timezone, timedelta

def test_fallback_verify_exact_caption_and_valid_timestamp_success():
    """TEST 1: Exact caption match + timestamp inside allowed publish attempt window succeeds."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("requests.get") as mock_get:
        # Container check returns FINISHED (falls through to account media check)
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Account media list returns 1 post with exact caption and valid timestamp
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_exact_101", "caption": "Exact Caption Match", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_101",
            access_token="valid_token",
            caption="Exact Caption Match",
            publish_started_at=now
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "media_exact_101"
        assert res["verification_source"] == "account_media_list"

def test_fallback_verify_substring_caption_rejected():
    """TEST 2: Substring / partial caption match is REJECTED."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_old_sale", "caption": "Sale", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = lambda *args, **kwargs: c_res if "102" in args[0] else m_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_102",
            access_token="valid_token",
            caption="Big Summer Sale",
            publish_started_at=now,
            max_wait_seconds=1.0,
            poll_interval=1.0
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_older_post_outside_time_window_rejected():
    """TEST 3: Older post with identical caption outside publish window is REJECTED."""
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=2)).isoformat() # 2 hours old (outside 15 min window)

    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_old_post", "caption": "Daily Update", "timestamp": old_ts}
            ]
        }
        mock_get.side_effect = lambda *args, **kwargs: c_res if "103" in args[0] else m_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_103",
            access_token="valid_token",
            caption="Daily Update",
            publish_started_at=now,
            max_wait_seconds=1.0,
            poll_interval=1.0
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_concurrent_identical_captions_fails_conservatively():
    """TEST 4: Two concurrent posts with identical captions return conservative failure (>1 matches)."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Account media returns TWO items matching exact caption inside timestamp window
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_job_a", "caption": "Concurrent Flash Sale", "timestamp": valid_ts},
                {"id": "media_job_b", "caption": "Concurrent Flash Sale", "timestamp": valid_ts}
            ]
        }
        mock_get.side_effect = lambda *args, **kwargs: c_res if "104" in args[0] else m_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_104",
            access_token="valid_token",
            caption="Concurrent Flash Sale",
            publish_started_at=now,
            max_wait_seconds=1.0,
            poll_interval=1.0
        )

        # Must fail conservatively (is_published=False) to avoid arbitrarily assigning media ID
        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_direct_container_status_published_success():
    """TEST 5: Direct container status == PUBLISHED succeeds immediately without media list fallback."""
    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "PUBLISHED", "id": "pub_media_direct_555"}
        mock_get.return_value = c_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_105",
            access_token="valid_token",
            caption="Any Caption"
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "pub_media_direct_555"
        assert res["verification_source"] == "container_status"
        assert mock_get.call_count == 1 # Media list endpoint was NOT called

def test_container_status_finished_does_not_mean_published():
    """TEST 6: Container status == FINISHED does NOT automatically mean published."""
    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {"data": []} # Empty media list
        mock_get.side_effect = lambda *args, **kwargs: c_res if "106" in args[0] else m_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_106",
            access_token="valid_token",
            caption="Unpublished Post",
            max_wait_seconds=1.0,
            poll_interval=1.0
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_fallback_verify_missing_timestamp_rejected():
    """Verify media item with exact caption match but missing or None timestamp is REJECTED."""
    now = datetime.now(timezone.utc)

    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200)
        c_res.json.return_value = {"status_code": "FINISHED"}

        # Media item has exact caption match but timestamp is None / missing
        m_res = MagicMock(status_code=200)
        m_res.json.return_value = {
            "data": [
                {"id": "media_no_ts", "caption": "Exact Caption", "timestamp": None}
            ]
        }
        mock_get.side_effect = lambda *args, **kwargs: c_res if "107" in args[0] else m_res

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_107",
            access_token="valid_token",
            caption="Exact Caption",
            publish_started_at=now,
            max_wait_seconds=1.0,
            poll_interval=1.0
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_datetime_timezone_utc_import_and_usage_no_nameerror():
    """Verify that process_single_job_in_thread executes datetime.now(timezone.utc) without NameError."""
    from app.services.publisher_service import PublishingEngine, InstagramPublisher
    publisher = InstagramPublisher()
    acc = MagicMock(id=1, account_id="17841400000000000", platform="instagram", access_token="tok_123", status="ACTIVE")
    mock_job = MagicMock(ig_container_id=None)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    
    with patch("app.services.publisher_service.SessionLocal", return_value=mock_db), \
         patch("app.repositories.social_account_repository.social_account_repo.get_by_id", return_value=acc), \
         patch("app.repositories.publishing_repository.publishing_repo.update_job_status"), \
         patch.object(publisher, "publish", return_value="pub_media_999"):
        
        engine = PublishingEngine()
        engine.ig_publisher = publisher
        res = engine.process_single_job_in_thread(
            job_id=99,
            social_account_id=1,
            caption="Test Timezone Import",
            public_media_url="https://example.com/img.jpg",
            is_video=False
        )

        assert res["status"] == "SUCCESS"
        assert res["external_id"] == "pub_media_999"

def test_unexpected_worker_exception_marks_job_failed():
    """Verify that an unexpected exception during worker execution marks job FAILED with UNEXPECTED_PUBLISH_ERROR."""
    from app.services.publisher_service import PublishingEngine
    acc = MagicMock(id=1, account_id="17841400000000000", platform="instagram", access_token="tok_123", status="ACTIVE")
    mock_job = MagicMock(ig_container_id=None)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job

    with patch("app.services.publisher_service.SessionLocal", return_value=mock_db), \
         patch("app.repositories.social_account_repository.social_account_repo.get_by_id", return_value=acc), \
         patch("app.repositories.publishing_repository.publishing_repo.update_job_status") as mock_update, \
         patch("app.services.publisher_service.InstagramPublisher.publish", side_effect=RuntimeError("Simulated unexpected crashes")):

        engine = PublishingEngine()
        res = engine.process_single_job_in_thread(
            job_id=100,
            social_account_id=1,
            caption="Test Crash Handling",
            public_media_url="https://example.com/img.jpg",
            is_video=False
        )

        assert res["status"] == "FAILED"
        assert res["error"] == "Unexpected worker error: Simulated unexpected crashes"

        # Confirm update_job_status was called with FAILED and UNEXPECTED_PUBLISH_ERROR
        failed_calls = [
            call for call in mock_update.call_args_list
            if len(call.args) >= 3 and call.args[1] == 100 and call.args[2] == "FAILED"
        ]
        assert len(failed_calls) > 0
        last_failed_kwargs = failed_calls[-1].kwargs
        assert last_failed_kwargs.get("error_code") == "UNEXPECTED_PUBLISH_ERROR"
        assert "Simulated unexpected crashes" in last_failed_kwargs.get("error_message", "")

def test_ambiguous_403_eventual_consistency_polling_finds_media_on_second_attempt_success():
    """Verify eventual consistency polling succeeds when post appears on second verification attempt."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("time.sleep") as mock_sleep, patch("requests.get") as mock_get:
        # Attempt 1: Container status FINISHED, media list empty
        c_res_1 = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        m_res_1 = MagicMock(status_code=200, json=lambda: {"data": []})

        # Attempt 2: Container status FINISHED, media list contains matching post
        c_res_2 = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        m_res_2 = MagicMock(status_code=200, json=lambda: {
            "data": [{"id": "eventual_media_202", "caption": "Polling Test", "timestamp": valid_ts}]
        })

        mock_get.side_effect = [c_res_1, m_res_1, c_res_2, m_res_2]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_202",
            access_token="valid_token",
            caption="Polling Test",
            publish_started_at=now,
            max_wait_seconds=10.0,
            poll_interval=2.0
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "eventual_media_202"
        assert res["verification_source"] == "account_media_list"
        assert mock_sleep.call_count == 1 # Slept once between attempt 1 and 2

def test_container_error_status_does_not_abort_and_finds_published_media_success():
    """Verify container status == ERROR does NOT early return, and account media list verification succeeds."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200, json=lambda: {"status_code": "ERROR"})
        m_res = MagicMock(status_code=200, json=lambda: {
            "data": [{"id": "live_media_303", "caption": "Live Post Despite ERROR", "timestamp": valid_ts}]
        })
        mock_get.side_effect = [c_res, m_res]

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_303",
            access_token="valid_token",
            caption="Live Post Despite ERROR",
            publish_started_at=now,
            max_wait_seconds=5.0,
            poll_interval=5.0
        )

        assert res["is_published"] is True
        assert res["published_media_id"] == "live_media_303"
        assert res["verification_source"] == "account_media_list"

def test_container_error_status_and_media_never_found_times_out():
    """Verify container status == ERROR and media never appearing returns FAILED after bounded polling timeout."""
    now = datetime.now(timezone.utc)

    with patch("time.sleep"), patch("requests.get") as mock_get:
        c_res = MagicMock(status_code=200, json=lambda: {"status_code": "ERROR"})
        m_res = MagicMock(status_code=200, json=lambda: {"data": []})
        mock_get.side_effect = [c_res, m_res, c_res, m_res] # 2 attempts

        res = meta_service.verify_instagram_container_published(
            ig_user_id="17841400000000000",
            creation_id="container_404",
            access_token="valid_token",
            caption="Failed Post",
            publish_started_at=now,
            max_wait_seconds=4.0,
            poll_interval=2.0
        )

        assert res["is_published"] is False
        assert res["verification_source"] == "verification_failed"

def test_ambiguous_recovery_calls_media_publish_exactly_once():
    """Verify media_publish POST is called exactly ONCE throughout ambiguous recovery verification."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("time.sleep"), patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        # Container creation success
        container_res = MagicMock(status_code=200, json=lambda: {"id": "container_once_505"})
        # Media publish returns 403 Rate Limit (Ambiguous)
        publish_res = MagicMock(status_code=403, json=lambda: {
            "error": {"message": "Application request limit reached", "code": 4, "error_subcode": 2207051}
        })
        mock_post.side_effect = [container_res, publish_res]

        # Status check FINISHED, account media list contains live item
        status_res = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        c_verify = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        m_verify = MagicMock(status_code=200, json=lambda: {
            "data": [{"id": "pub_once_505", "caption": "Single Publish Test", "timestamp": valid_ts}]
        })
        mock_get.side_effect = [status_res, c_verify, m_verify]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token",
            caption="Single Publish Test",
            image_url="https://example.com/image.jpg",
            is_video=False
        )

        assert res["id"] == "pub_once_505"
        assert res["status"] == "published"
        # Confirm media_publish POST endpoint was called exactly once (1 container create + 1 publish = 2 total POSTs)
        post_urls = [call.args[0] for call in mock_post.call_args_list]
        publish_calls = [url for url in post_urls if "media_publish" in url]
        assert len(publish_calls) == 1

def test_ambiguous_recovery_creates_no_new_containers_during_verification():
    """Verify NO new container is created during verification polling loop."""
    now = datetime.now(timezone.utc)
    valid_ts = now.isoformat()

    with patch("time.sleep"), patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        container_res = MagicMock(status_code=200, json=lambda: {"id": "container_nocreate_606"})
        publish_res = MagicMock(status_code=403, json=lambda: {
            "error": {"message": "Application request limit reached", "code": 4, "error_subcode": 2207051}
        })
        mock_post.side_effect = [container_res, publish_res]

        status_res = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        c_verify = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
        m_verify = MagicMock(status_code=200, json=lambda: {
            "data": [{"id": "pub_nocreate_606", "caption": "No New Container Test", "timestamp": valid_ts}]
        })
        mock_get.side_effect = [status_res, c_verify, m_verify]

        res = meta_service.publish_to_instagram_business(
            ig_user_id="17841400000000000",
            access_token="valid_token",
            caption="No New Container Test",
            image_url="https://example.com/image.jpg",
            is_video=False
        )

        assert res["id"] == "pub_nocreate_606"
        # Exactly 1 container creation POST occurred before media_publish, none during verification
        post_urls = [call.args[0] for call in mock_post.call_args_list]
        container_create_calls = [url for url in post_urls if "media_publish" not in url]
        assert len(container_create_calls) == 1





