import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.meta_ad import MetaAd
from app.models.post import Post
from app.repositories.social_comment_repository import social_comment_repo
from app.core.security import create_access_token
from app.core.security_encryption import encrypt_token

client = TestClient(app)

@pytest.fixture
def test_user(db_session: Session):
    user = User(
        email=f"audit_user_{datetime.now(timezone.utc).timestamp()}@socialai.com",
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Audit Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User):
    token = create_access_token(subject=str(test_user.id), role=test_user.role or "user")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user(db_session: Session):
    user = User(
        email=f"other_audit_user_{datetime.now(timezone.utc).timestamp()}@socialai.com",
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Other Audit User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_accounts(db_session: Session, test_user: User, other_user: User):
    acc1 = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="page_1001",
        account_name="Primary Brand Page",
        status="CONNECTED",
        access_token=encrypt_token("EAAB_test_token_1")
    )
    acc2 = SocialAccount(
        user_id=test_user.id,
        platform="facebook",
        account_id="page_1002",
        account_name="Secondary Brand Page",
        status="CONNECTED",
        access_token=encrypt_token("EAAB_test_token_2")
    )
    other_acc = SocialAccount(
        user_id=other_user.id,
        platform="facebook",
        account_id="page_9999",
        account_name="Other User Page",
        status="CONNECTED",
        access_token=encrypt_token("EAAB_other_token")
    )
    db_session.add_all([acc1, acc2, other_acc])
    db_session.commit()
    db_session.refresh(acc1)
    db_session.refresh(acc2)
    db_session.refresh(other_acc)
    return {"acc1": acc1, "acc2": acc2, "other_acc": other_acc}


def test_sorting_newest_uses_event_timestamp(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that comments are sorted by actual Meta creation event_timestamp (descending)."""
    acc = test_accounts["acc1"]
    base_time = datetime(2026, 9, 5, 10, 0, 0, tzinfo=timezone.utc)

    # Insert in arbitrary DB insertion order
    c_mid = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_mid_1030",
        comment_text="Comment at 10:30 AM",
        event_timestamp=base_time + timedelta(minutes=30),
        webhook_object="page"
    )
    c_old = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_old_1000",
        comment_text="Comment at 10:00 AM",
        event_timestamp=base_time,
        webhook_object="page"
    )
    c_new = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_new_1100",
        comment_text="Comment at 11:00 AM",
        event_timestamp=base_time + timedelta(hours=1),
        webhook_object="page"
    )
    db_session.add_all([c_mid, c_old, c_new])
    db_session.commit()

    # Query via API with default sort_order (desc)
    res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["external_comment_id"] == "c_new_1100"
    assert data[1]["external_comment_id"] == "c_mid_1030"
    assert data[2]["external_comment_id"] == "c_old_1000"

    # Query via API explicitly with sort_order=desc
    res_desc = client.get("/api/v1/social-comments/?sort_order=desc", headers=auth_headers)
    assert res_desc.status_code == 200
    data_desc = res_desc.json()
    assert [c["external_comment_id"] for c in data_desc] == ["c_new_1100", "c_mid_1030", "c_old_1000"]


def test_sorting_oldest_uses_event_timestamp(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that comments can be sorted oldest-first using event_timestamp (ascending)."""
    acc = test_accounts["acc1"]
    base_time = datetime(2026, 9, 5, 8, 0, 0, tzinfo=timezone.utc)

    c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_early",
        comment_text="Early morning comment",
        event_timestamp=base_time,
        webhook_object="page"
    )
    c2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_late",
        comment_text="Late morning comment",
        event_timestamp=base_time + timedelta(hours=3),
        webhook_object="page"
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    res_asc = client.get("/api/v1/social-comments/?sort_order=asc", headers=auth_headers)
    assert res_asc.status_code == 200
    data_asc = res_asc.json()
    assert len(data_asc) == 2
    assert data_asc[0]["external_comment_id"] == "c_early"
    assert data_asc[1]["external_comment_id"] == "c_late"


def test_sorting_fallback_to_created_at(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that sorting safely falls back to created_at when event_timestamp is NULL."""
    acc = test_accounts["acc1"]
    now = datetime.now(timezone.utc)

    c_no_ts_1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_no_ts_1",
        comment_text="No event timestamp 1",
        event_timestamp=None,
        created_at=now - timedelta(minutes=10),
        webhook_object="page"
    )
    c_no_ts_2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_no_ts_2",
        comment_text="No event timestamp 2",
        event_timestamp=None,
        created_at=now,
        webhook_object="page"
    )
    db_session.add_all([c_no_ts_1, c_no_ts_2])
    db_session.commit()

    res_desc = client.get("/api/v1/social-comments/?sort_order=desc", headers=auth_headers)
    assert res_desc.status_code == 200
    data_desc = res_desc.json()
    assert data_desc[0]["external_comment_id"] == "c_no_ts_2"
    assert data_desc[1]["external_comment_id"] == "c_no_ts_1"


def test_invalid_sort_order_defaults_to_desc(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that an invalid sort_order string safely falls back to descending order."""
    acc = test_accounts["acc1"]
    base_time = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)

    c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_alpha",
        comment_text="Older",
        event_timestamp=base_time,
        webhook_object="page"
    )
    c2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_beta",
        comment_text="Newer",
        event_timestamp=base_time + timedelta(hours=1),
        webhook_object="page"
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Pass invalid sort_order
    res = client.get("/api/v1/social-comments/?sort_order=INVALID_SQL_INJECTION", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data[0]["external_comment_id"] == "c_beta"
    assert data[1]["external_comment_id"] == "c_alpha"


def test_parent_comment_count_strictly_excludes_replies(db_session: Session, test_user: User, test_accounts, auth_headers):
    """
    Verify top-level comment count vs replies:
    3 parent comments, 4 replies (2 Meta child replies + 2 owner replies) -> count is exactly 3.
    """
    acc = test_accounts["acc1"]
    now = datetime.now(timezone.utc)

    # 3 Top-level comments
    p1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="parent_1",
        comment_text="Parent comment 1",
        event_timestamp=now,
        webhook_object="page"
    )
    p2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="parent_2",
        comment_text="Parent comment 2",
        event_timestamp=now + timedelta(seconds=1),
        webhook_object="page"
    )
    p3 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="parent_3",
        comment_text="Parent comment 3",
        event_timestamp=now + timedelta(seconds=2),
        webhook_object="page"
    )
    db_session.add_all([p1, p2, p3])
    db_session.commit()
    db_session.refresh(p1)
    db_session.refresh(p2)

    # 2 Meta child comments (replies to parent_1)
    r_meta1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="meta_reply_1",
        parent_comment_id="parent_1",
        comment_text="Customer reply to parent 1",
        commenter_name="Customer Alice",
        event_timestamp=now + timedelta(seconds=10),
        webhook_object="page"
    )
    r_meta2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="meta_reply_2",
        parent_comment_id="parent_1",
        comment_text="Customer reply 2 to parent 1",
        commenter_name="Customer Bob",
        event_timestamp=now + timedelta(seconds=20),
        webhook_object="page"
    )
    db_session.add_all([r_meta1, r_meta2])
    db_session.commit()

    # 2 Owner replies (SocialCommentReply)
    r_owner1 = SocialCommentReply(
        comment_id=p1.id,
        user_id=test_user.id,
        platform="facebook",
        message="Brand reply to parent 1",
        external_reply_id="ext_owner_rep_1",
        status="SUCCESS",
        created_at=now + timedelta(seconds=30)
    )
    r_owner2 = SocialCommentReply(
        comment_id=p2.id,
        user_id=test_user.id,
        platform="facebook",
        message="Brand reply to parent 2",
        external_reply_id="ext_owner_rep_2",
        status="SUCCESS",
        created_at=now + timedelta(seconds=35)
    )
    db_session.add_all([r_owner1, r_owner2])
    db_session.commit()

    # Verify repository counts
    top_level_count = social_comment_repo.count_by_user_id(db_session, test_user.id, top_level_only=True)
    reply_count = social_comment_repo.count_replies_by_user_id(db_session, test_user.id)
    assert top_level_count == 3
    assert reply_count == 4  # 2 meta child comments + 2 owner replies

    # Verify Overview API response
    overview_res = client.get("/api/v1/social-comments/overview", headers=auth_headers)
    assert overview_res.status_code == 200
    ov_data = overview_res.json()
    assert ov_data["top_level_comment_count"] == 3
    assert ov_data["reply_count"] == 4
    assert ov_data["total_interaction_count"] == 7
    assert ov_data["total_comments"] == 3

    # Verify GET /social-comments/ returns 3 top-level items with nested replies
    list_res = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert list_res.status_code == 200
    comments_data = list_res.json()
    assert len(comments_data) == 3

    # Check parent_1 nested replies
    p1_item = next(c for c in comments_data if c["external_comment_id"] == "parent_1")
    assert len(p1_item["replies"]) == 3  # 1 owner reply + 2 meta child replies

    # Verify reply source attribution
    meta_replies = [r for r in p1_item["replies"] if r["source"] == "meta"]
    owner_replies = [r for r in p1_item["replies"] if r["source"] == "owner"]
    assert len(meta_replies) == 2
    assert len(owner_replies) == 1
    assert meta_replies[0]["commenter_name"] == "Customer Alice"
    assert meta_replies[0]["created_at"] is not None


def test_account_isolation_in_comments_and_counts(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that comments belonging to Account 1 never appear when filtering by Account 2."""
    acc1 = test_accounts["acc1"]
    acc2 = test_accounts["acc2"]
    now = datetime.now(timezone.utc)

    c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        platform="facebook",
        external_comment_id="acc1_comment",
        comment_text="On Account 1",
        event_timestamp=now,
        webhook_object="page"
    )
    c2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc2.id,
        platform="facebook",
        external_comment_id="acc2_comment",
        comment_text="On Account 2",
        event_timestamp=now + timedelta(minutes=1),
        webhook_object="page"
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    # Query all
    res_all = client.get("/api/v1/social-comments/", headers=auth_headers)
    assert len(res_all.json()) == 2

    # Query Account 1 only
    res_acc1 = client.get(f"/api/v1/social-comments/?social_account_id={acc1.id}", headers=auth_headers)
    assert res_acc1.status_code == 200
    data_acc1 = res_acc1.json()
    assert len(data_acc1) == 1
    assert data_acc1[0]["external_comment_id"] == "acc1_comment"

    # Query Account 2 only
    res_acc2 = client.get(f"/api/v1/social-comments/?social_account_id={acc2.id}", headers=auth_headers)
    assert res_acc2.status_code == 200
    data_acc2 = res_acc2.json()
    assert len(data_acc2) == 1
    assert data_acc2[0]["external_comment_id"] == "acc2_comment"

    # Query Overview for Account 1 only
    ov_acc1 = client.get(f"/api/v1/social-comments/overview?social_account_id={acc1.id}", headers=auth_headers)
    assert ov_acc1.status_code == 200
    assert ov_acc1.json()["top_level_comment_count"] == 1


def test_replied_and_unreplied_filters_with_sorting(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify that replied and unreplied filters work seamlessly with sort_order."""
    acc = test_accounts["acc1"]
    now = datetime.now(timezone.utc)

    # c_unreplied: No replies
    c_unreplied = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_unrep",
        comment_text="Needs reply",
        event_timestamp=now,
        webhook_object="page"
    )
    # c_replied: Has owner reply
    c_replied = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        platform="facebook",
        external_comment_id="c_rep",
        comment_text="Already replied",
        event_timestamp=now + timedelta(minutes=5),
        webhook_object="page"
    )
    db_session.add_all([c_unreplied, c_replied])
    db_session.commit()
    db_session.refresh(c_replied)

    rep = SocialCommentReply(
        comment_id=c_replied.id,
        user_id=test_user.id,
        platform="facebook",
        message="Thank you!",
        external_reply_id="ext_rep_1",
        status="SUCCESS",
        created_at=now + timedelta(minutes=6)
    )
    db_session.add(rep)
    db_session.commit()

    # Filter unreplied
    res_unrep = client.get("/api/v1/social-comments/?reply_status=unreplied", headers=auth_headers)
    assert res_unrep.status_code == 200
    data_unrep = res_unrep.json()
    assert len(data_unrep) == 1
    assert data_unrep[0]["external_comment_id"] == "c_unrep"

    # Filter replied
    res_rep = client.get("/api/v1/social-comments/?reply_status=replied", headers=auth_headers)
    assert res_rep.status_code == 200
    data_rep = res_rep.json()
    assert len(data_rep) == 1
    assert data_rep[0]["external_comment_id"] == "c_rep"


def test_ad_and_post_endpoints_sort_order(db_session: Session, test_user: User, test_accounts, auth_headers):
    """Verify sort_order works on GET /ads/{id} and GET /posts/{id} endpoints."""
    acc = test_accounts["acc1"]
    now = datetime.now(timezone.utc)

    # Create MetaAd
    ad = MetaAd(
        user_id=test_user.id,
        meta_ad_account_id="act_12345",
        meta_ad_id="ad_998877",
        name="Test Campaign Ad",
        facebook_page_id=acc.account_id,
        facebook_post_id="post_ad_123"
    )
    db_session.add(ad)
    db_session.commit()
    db_session.refresh(ad)

    # Add 2 comments to this ad with different timestamps
    c_early = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        meta_ad_id=ad.id,
        platform="facebook",
        external_comment_id="ad_c_early",
        comment_text="Early Ad Comment",
        event_timestamp=now,
        webhook_object="ad_comment"
    )
    c_late = SocialComment(
        user_id=test_user.id,
        social_account_id=acc.id,
        meta_ad_id=ad.id,
        platform="facebook",
        external_comment_id="ad_c_late",
        comment_text="Late Ad Comment",
        event_timestamp=now + timedelta(hours=2),
        webhook_object="ad_comment"
    )
    db_session.add_all([c_early, c_late])
    db_session.commit()

    # GET /ads/{ad_id} desc
    res_ad_desc = client.get(f"/api/v1/social-comments/ads/{ad.id}?sort_order=desc", headers=auth_headers)
    assert res_ad_desc.status_code == 200
    ad_comments_desc = res_ad_desc.json()["comments"]
    assert len(ad_comments_desc) == 2
    assert ad_comments_desc[0]["external_comment_id"] == "ad_c_late"
    assert ad_comments_desc[1]["external_comment_id"] == "ad_c_early"

    # GET /ads/{ad_id} asc
    res_ad_asc = client.get(f"/api/v1/social-comments/ads/{ad.id}?sort_order=asc", headers=auth_headers)
    assert res_ad_asc.status_code == 200
    ad_comments_asc = res_ad_asc.json()["comments"]
    assert ad_comments_asc[0]["external_comment_id"] == "ad_c_early"
    assert ad_comments_asc[1]["external_comment_id"] == "ad_c_late"


def test_engagement_metrics_scoping_posts_ads_and_all(db_session: Session, test_user: User, test_accounts, auth_headers):
    """
    Verify engagement overview metrics are accurately scoped for:
    1. Organic posts (excludes ads)
    2. Meta ads (excludes organic posts)
    3. All (combines both)
    4. Account filtering
    5. Top-level vs replies distinction
    """
    acc1 = test_accounts["acc1"]
    acc2 = test_accounts["acc2"]
    now = datetime.now(timezone.utc)

    # 1. Create 2 Organic Posts comments on acc1
    post1_c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        platform="facebook",
        external_comment_id="p1_c1",
        external_post_id="post_1001",
        comment_text="Organic post 1 comment 1",
        event_timestamp=now,
        webhook_object="page"
    )
    post1_c2 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        platform="facebook",
        external_comment_id="p1_c2",
        external_post_id="post_1001",
        comment_text="Organic post 1 comment 2",
        event_timestamp=now + timedelta(minutes=5),
        webhook_object="page"
    )
    # 1 Organic Post comment on acc2
    post2_c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc2.id,
        platform="facebook",
        external_comment_id="p2_c1",
        external_post_id="post_2001",
        comment_text="Organic post 2 comment 1",
        event_timestamp=now + timedelta(minutes=10),
        webhook_object="page"
    )
    db_session.add_all([post1_c1, post1_c2, post2_c1])
    db_session.commit()
    db_session.refresh(post1_c1)
    db_session.refresh(post1_c2)

    # 1 Meta child reply to post1_c1
    post1_r1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        platform="facebook",
        external_comment_id="p1_r1",
        parent_comment_id="p1_c1",
        external_post_id="post_1001",
        comment_text="Customer reply on organic post",
        event_timestamp=now + timedelta(minutes=15),
        webhook_object="page"
    )
    # 1 Owner reply to post1_c2
    post1_owner_reply = SocialCommentReply(
        comment_id=post1_c2.id,
        user_id=test_user.id,
        platform="facebook",
        external_reply_id="p1_own_r1",
        message="Brand reply on organic post",
        status="SUCCESS"
    )
    db_session.add_all([post1_r1, post1_owner_reply])
    db_session.commit()

    # 2. Create 1 Meta Ad on acc1 with 1 comment and 1 reply
    ad1 = MetaAd(
        user_id=test_user.id,
        meta_ad_account_id="act_555",
        meta_ad_id="ad_55501",
        name="Summer Ad 1",
        facebook_page_id=acc1.account_id
    )
    db_session.add(ad1)
    db_session.commit()
    db_session.refresh(ad1)

    ad1_c1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        meta_ad_id=ad1.id,
        platform="facebook",
        external_comment_id="ad1_c1",
        comment_text="Ad 1 comment 1",
        event_timestamp=now + timedelta(minutes=20),
        webhook_object="ad_comment"
    )
    db_session.add(ad1_c1)
    db_session.commit()
    db_session.refresh(ad1_c1)

    ad1_r1 = SocialComment(
        user_id=test_user.id,
        social_account_id=acc1.id,
        meta_ad_id=ad1.id,
        platform="facebook",
        external_comment_id="ad1_r1",
        parent_comment_id="ad1_c1",
        comment_text="Ad 1 customer reply",
        event_timestamp=now + timedelta(minutes=25),
        webhook_object="ad_comment"
    )
    db_session.add(ad1_r1)
    db_session.commit()

    # Query 1: Overview with scope=posts (All Accounts)
    # Expect: 3 top-level organic (2 on acc1 + 1 on acc2), 2 organic replies (1 meta + 1 owner)
    res_posts = client.get("/api/v1/social-comments/overview?scope=posts", headers=auth_headers)
    assert res_posts.status_code == 200
    data_posts = res_posts.json()
    assert data_posts["top_level_comment_count"] == 3
    assert data_posts["reply_count"] == 2
    assert data_posts["total_interaction_count"] == 5
    assert data_posts["posts_metrics"]["top_level_comment_count"] == 3
    assert data_posts["posts_metrics"]["reply_count"] == 2

    # Query 2: Overview with scope=ads (All Accounts)
    # Expect: 1 top-level ad comment, 1 ad reply
    res_ads = client.get("/api/v1/social-comments/overview?scope=ads", headers=auth_headers)
    assert res_ads.status_code == 200
    data_ads = res_ads.json()
    assert data_ads["top_level_comment_count"] == 1
    assert data_ads["reply_count"] == 1
    assert data_ads["total_interaction_count"] == 2
    assert data_ads["ads_metrics"]["top_level_comment_count"] == 1
    assert data_ads["ads_metrics"]["reply_count"] == 1

    # Query 3: Overview with scope=all (All Accounts)
    # Expect: 4 top-level comments (3 organic + 1 ad), 3 replies (2 organic + 1 ad), total = 7
    res_all = client.get("/api/v1/social-comments/overview?scope=all", headers=auth_headers)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["top_level_comment_count"] == 4
    assert data_all["reply_count"] == 3
    assert data_all["total_interaction_count"] == 7
    assert data_all["all_metrics"]["top_level_comment_count"] == 4
    assert data_all["all_metrics"]["reply_count"] == 3

    # Query 4: Overview with account filter (acc1 only)
    # On acc1: 2 organic posts + 1 ad = 3 top-level, 2 organic replies + 1 ad reply = 3 replies
    res_acc1_posts = client.get(f"/api/v1/social-comments/overview?scope=posts&social_account_id={acc1.id}", headers=auth_headers)
    assert res_acc1_posts.status_code == 200
    data_acc1_posts = res_acc1_posts.json()
    assert data_acc1_posts["top_level_comment_count"] == 2
    assert data_acc1_posts["reply_count"] == 2
    assert data_acc1_posts["total_interaction_count"] == 4

