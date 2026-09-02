import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.meta_ad import MetaAd
from app.services.meta_service import meta_service, extract_page_id_from_post_id
from app.core.security_encryption import encrypt_token

def test_extract_page_id_from_post_id():
    """Verify Page ID extraction from standard post_id strings and invalid inputs."""
    # Standard format {page_id}_{post_id}
    assert extract_page_id_from_post_id("1001432206614811_1524306126380444") == "1001432206614811"
    assert extract_page_id_from_post_id("711139875422034_122142588518963628") == "711139875422034"
    
    # Invalid formats
    assert extract_page_id_from_post_id("invalidpostid") is None
    assert extract_page_id_from_post_id("abc_12345") is None
    assert extract_page_id_from_post_id("") is None
    assert extract_page_id_from_post_id(None) is None


def test_exact_page_match_selects_correct_token(db_session: Session):
    """
    Test 1: Given post 1001432206614811_123456 and connected accounts [1001432206614811, 1257381927456142],
    verifies exact matching token for 1001432206614811 is selected and API request is made.
    """
    user = User(email="exact_match@test.com", full_name="Exact Match User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa1 = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Matching Page", access_token=encrypt_token("token_page_1"), status="CONNECTED"
    )
    sa2 = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1257381927456142",
        account_name="Other Page", access_token=encrypt_token("token_page_2"), status="CONNECTED"
    )
    db_session.add_all([sa1, sa2])
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_111", meta_ad_id="ad_exact",
        name="Exact Ad", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_123456"
    )
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = ([], {"status_code": 200, "is_permission_error": False})
        
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_111")
        
        assert res["success"] is True
        assert res["posts_processed"] == 1
        assert res["pages_not_connected"] == 0
        assert res["permission_errors"] == 0

        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args.kwargs
        assert call_kwargs["access_token"] == "token_page_1"
        assert call_kwargs["post_id"] == "1001432206614811_123456"
        assert call_kwargs["page_id"] == "1001432206614811"


def test_no_matching_page_skips_api_call(db_session: Session):
    """
    Test 2: Given post 711139875422034_123456 and connected accounts [1001432206614811, 1257381927456142],
    verifies no token is selected, Meta API is NOT called, post is skipped with PAGE_NOT_CONNECTED,
    pages_not_connected increments, permission_errors does NOT increment.
    """
    user = User(email="no_match@test.com", full_name="No Match User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa1 = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Page 1", access_token=encrypt_token("token_page_1"), status="CONNECTED"
    )
    sa2 = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1257381927456142",
        account_name="Page 2", access_token=encrypt_token("token_page_2"), status="CONNECTED"
    )
    db_session.add_all([sa1, sa2])
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_222", meta_ad_id="ad_unconnected",
        name="Unconnected Ad", facebook_page_id="711139875422034", facebook_post_id="711139875422034_123456"
    )
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_222")
        
        assert res["success"] is True
        assert res["reconnect_required"] is False
        assert res["posts_processed"] == 0
        assert res["pages_not_connected"] == 1
        assert res["permission_errors"] == 0
        assert res["skipped_posts"] == 1

        mock_fetch.assert_not_called()


def test_prevent_cross_page_fallback(db_session: Session):
    """
    Test 3: Explicitly verify that the old fallback behavior cannot happen.
    Given post page ID 711139875422034 and connected account 1257381927456142,
    verifies token for 1257381927456142 is NEVER passed to Graph API request.
    """
    user = User(email="prevent_fallback@test.com", full_name="Fallback User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1257381927456142",
        account_name="Different Page", access_token=encrypt_token("token_different_page"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_333", meta_ad_id="ad_fallback",
        name="Fallback Ad", facebook_page_id="711139875422034", facebook_post_id="711139875422034_122142588518963628"
    )
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_333")
        
        assert res["success"] is True
        assert res["pages_not_connected"] == 1
        mock_fetch.assert_not_called()


def test_invalid_post_id_skips_api_call(db_session: Session):
    """
    Test 4: Given malformed post_id without valid Page ID,
    verifies no Graph API request is made, reason INVALID_POST_ID, invalid_post_ids increments.
    """
    user = User(email="invalid_post@test.com", full_name="Invalid Post User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Connected Page", access_token=encrypt_token("token_page_1"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad = MetaAd(
        user_id=user.id, meta_ad_account_id="act_444", meta_ad_id="ad_invalid",
        name="Invalid Post Ad", facebook_page_id=None, facebook_post_id="invalid_post_id_format"
    )
    db_session.add(ad)
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_444")
        
        assert res["success"] is True
        assert res["invalid_post_ids"] == 1
        assert res["posts_processed"] == 0
        mock_fetch.assert_not_called()


def test_mixed_batch_sync(db_session: Session):
    """
    Test 5: Create a batch containing:
    - one exact matching Page (1001432206614811_111)
    - one non-connected Page (711139875422034_222)
    - one invalid post ID (invalid_333)
    Verifies exact match is synchronized, non-connected skipped, invalid skipped, counters accurate.
    """
    user = User(email="mixed_batch@test.com", full_name="Mixed Batch User", hashed_password="pw", is_active=True, role="Editor")
    db_session.add(user)
    db_session.commit()

    sa = SocialAccount(
        user_id=user.id, platform="facebook", account_id="1001432206614811",
        account_name="Exact Page", access_token=encrypt_token("token_exact"), status="CONNECTED"
    )
    db_session.add(sa)
    db_session.commit()

    ad1 = MetaAd(user_id=user.id, meta_ad_account_id="act_555", meta_ad_id="ad1", facebook_page_id="1001432206614811", facebook_post_id="1001432206614811_111")
    ad2 = MetaAd(user_id=user.id, meta_ad_account_id="act_555", meta_ad_id="ad2", facebook_page_id="711139875422034", facebook_post_id="711139875422034_222")
    ad3 = MetaAd(user_id=user.id, meta_ad_account_id="act_555", meta_ad_id="ad3", facebook_page_id=None, facebook_post_id="invalid_333")
    db_session.add_all([ad1, ad2, ad3])
    db_session.commit()

    with patch.object(meta_service, "fetch_comments_for_facebook_post") as mock_fetch:
        mock_fetch.return_value = ([], {"status_code": 200, "is_permission_error": False})
        
        res = meta_service.sync_comments_for_meta_ads(db=db_session, user_id=user.id, meta_ad_account_id="act_555")
        
        assert res["success"] is True
        assert res["reconnect_required"] is False
        assert res["ads_checked"] == 3
        assert res["posts_processed"] == 1
        assert res["pages_not_connected"] == 1
        assert res["invalid_post_ids"] == 1
        assert res["skipped_posts"] == 2
        assert res["permission_errors"] == 0

        # Verify only the exact matching post triggered an API call
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args.kwargs["post_id"] == "1001432206614811_111"
        assert mock_fetch.call_args.kwargs["access_token"] == "token_exact"
