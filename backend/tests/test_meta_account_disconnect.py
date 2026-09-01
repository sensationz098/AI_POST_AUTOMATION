import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment
from app.models.social_comment_reply import SocialCommentReply
from app.models.post import Post, PostStatus
from app.models.publishing_batch import PublishingBatch, PublishingJob, JobStatus
from app.models.brand import BrandProfile
from app.models.meta_account import MetaAccount
from app.core.security_encryption import encrypt_token
from app.repositories.social_account_repository import social_account_repo

client = TestClient(app)

@pytest.fixture
def disconnect_test_user(db_session: Session):
    email = f"disconnect_user_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    user = User(
        email=email,
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Disconnect Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(disconnect_test_user: User):
    from app.core.security import create_access_token
    token = create_access_token(subject=str(disconnect_test_user.id), role=disconnect_test_user.role or "user")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user(db_session: Session):
    email = f"other_disc_user_{datetime.now(timezone.utc).timestamp()}@socialai.com"
    user = User(
        email=email,
        hashed_password="HashedPassword123!",
        is_active=True,
        full_name="Other User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def brand(db_session: Session, disconnect_test_user: User):
    b = BrandProfile(
        name="Disconnect Test Brand",
        user_id=disconnect_test_user.id,
        brand_colors=[],
        tone_of_voice="Professional",
        cta_style="Direct"
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)

    meta = MetaAccount(
        brand_id=b.id,
        facebook_page_id="fb_page_100",
        facebook_page_name="Disconnect FB Page",
        instagram_account_id="ig_acc_200",
        instagram_username="disconnect_ig",
        is_connected=True
    )
    db_session.add(meta)
    db_session.commit()
    return b

@pytest.fixture
def fb_account(db_session: Session, disconnect_test_user: User, brand: BrandProfile):
    acc = SocialAccount(
        user_id=disconnect_test_user.id,
        brand_id=brand.id,
        platform="facebook",
        account_id="fb_page_100",
        account_name="Disconnect FB Page",
        access_token=encrypt_token("EAANNCr_fb_token_123"),
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc

@pytest.fixture
def ig_account(db_session: Session, disconnect_test_user: User, brand: BrandProfile):
    acc = SocialAccount(
        user_id=disconnect_test_user.id,
        brand_id=brand.id,
        platform="instagram",
        account_id="ig_acc_200",
        account_name="disconnect_ig",
        access_token=encrypt_token("EAANNCr_ig_token_456"),
        status="CONNECTED"
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(acc)
    return acc


def test_disconnect_single_account_without_comments(client: TestClient, auth_headers: dict, fb_account: SocialAccount, db_session: Session):
    """Scenario A: Disconnecting an account without any comments succeeds cleanly."""
    acc_id = fb_account.id
    res = client.delete(f"/api/v1/social-accounts/{acc_id}", headers=auth_headers)
    assert res.status_code == 204

    deleted_acc = db_session.query(SocialAccount).filter(SocialAccount.id == acc_id).first()
    assert deleted_acc is None


def test_disconnect_single_account_with_comments_and_replies(client: TestClient, auth_headers: dict, disconnect_test_user: User, fb_account: SocialAccount, db_session: Session):
    """Scenario D & E: Disconnecting an account with comments and comment replies succeeds without null constraint violations."""
    # 1. Create dependent comment
    comment = SocialComment(
        user_id=disconnect_test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="comment_to_del_101",
        comment_text="Test comment before disconnect",
        webhook_object="page"
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # 2. Create dependent reply
    reply = SocialCommentReply(
        comment_id=comment.id,
        user_id=disconnect_test_user.id,
        platform="facebook",
        message="Reply before disconnect",
        external_reply_id="reply_to_del_202",
        status="SUCCESS"
    )
    db_session.add(reply)
    db_session.commit()

    comment_id = comment.id
    reply_id = reply.id
    acc_id = fb_account.id

    # 3. Disconnect account via DELETE /api/v1/social-accounts/{account_id}
    res = client.delete(f"/api/v1/social-accounts/{acc_id}", headers=auth_headers)
    assert res.status_code == 204

    # 4. Verify account, comments, and replies are removed cleanly
    assert db_session.query(SocialAccount).filter(SocialAccount.id == acc_id).first() is None
    assert db_session.query(SocialComment).filter(SocialComment.id == comment_id).first() is None
    assert db_session.query(SocialCommentReply).filter(SocialCommentReply.id == reply_id).first() is None


def test_disconnect_account_with_publishing_jobs(client: TestClient, auth_headers: dict, disconnect_test_user: User, brand: BrandProfile, fb_account: SocialAccount, db_session: Session):
    """Scenario F: Disconnecting an account with publishing jobs succeeds without foreign key errors."""
    post = Post(
        brand_id=brand.id,
        user_id=disconnect_test_user.id,
        caption="Post for publishing job test",
        platforms=["facebook"]
    )
    db_session.add(post)
    db_session.commit()

    batch = PublishingBatch(
        post_id=post.id,
        user_id=disconnect_test_user.id,
        status="SUCCESS"
    )
    db_session.add(batch)
    db_session.commit()

    job = PublishingJob(
        batch_id=batch.id,
        social_account_id=fb_account.id,
        platform="facebook",
        status="SUCCESS"
    )
    db_session.add(job)
    db_session.commit()

    job_id = job.id
    acc_id = fb_account.id

    res = client.delete(f"/api/v1/social-accounts/{acc_id}", headers=auth_headers)
    assert res.status_code == 204

    assert db_session.query(SocialAccount).filter(SocialAccount.id == acc_id).first() is None
    assert db_session.query(PublishingJob).filter(PublishingJob.id == job_id).first() is None


def test_disconnect_all_meta_accounts(client: TestClient, auth_headers: dict, disconnect_test_user: User, fb_account: SocialAccount, ig_account: SocialAccount, db_session: Session):
    """Scenario B & G: Disconnecting all Meta accounts removes all accounts and dependent comments/jobs."""
    c1 = SocialComment(
        user_id=disconnect_test_user.id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="c_fb_all",
        webhook_object="page"
    )
    c2 = SocialComment(
        user_id=disconnect_test_user.id,
        social_account_id=ig_account.id,
        platform="instagram",
        external_comment_id="c_ig_all",
        webhook_object="instagram"
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    res = client.delete("/api/v1/social-accounts/disconnect-all", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2

    # Verify all accounts and comments are removed
    user_accounts = db_session.query(SocialAccount).filter(SocialAccount.user_id == disconnect_test_user.id).all()
    user_comments = db_session.query(SocialComment).filter(SocialComment.user_id == disconnect_test_user.id).all()
    assert len(user_accounts) == 0
    assert len(user_comments) == 0


def test_user_cannot_disconnect_another_users_account(client: TestClient, other_user: User, fb_account: SocialAccount):
    """Verify tenant isolation: User A cannot disconnect User B's social account."""
    from app.core.security import create_access_token
    other_headers = {"Authorization": f"Bearer {create_access_token(subject=str(other_user.id), role='user')}"}

    res = client.delete(f"/api/v1/social-accounts/{fb_account.id}", headers=other_headers)
    assert res.status_code == 404


def test_reconnect_after_disconnect(disconnect_test_user: User, fb_account: SocialAccount, db_session: Session):
    """Scenario H & I: Reconnecting Meta after disconnecting works cleanly without old leftover data interference."""
    acc_id_str = fb_account.account_id
    user_id = disconnect_test_user.id

    # 1. Add comment
    c = SocialComment(
        user_id=user_id,
        social_account_id=fb_account.id,
        platform="facebook",
        external_comment_id="recon_c_1",
        webhook_object="page"
    )
    db_session.add(c)
    db_session.commit()

    # 2. Delete social account
    deleted = social_account_repo.delete(db_session, fb_account.id, user_id)
    assert deleted is True

    # 3. Reconnect account via social_account_repo.create_or_update
    new_acc = social_account_repo.create_or_update(
        db=db_session,
        user_id=user_id,
        platform="facebook",
        account_id=acc_id_str,
        account_name="Reconnected FB Page",
        access_token="NEW_RECONNECTED_TOKEN"
    )

    assert new_acc is not None
    assert new_acc.account_name == "Reconnected FB Page"
    assert new_acc.status == "CONNECTED"


def test_transaction_rollback_on_failure(disconnect_test_user: User, fb_account: SocialAccount, db_session: Session):
    """Verify transaction safety: If deletion fails, session rolls back and leaves no partial deletion."""
    with patch.object(db_session, "commit", side_effect=Exception("Database commit error")):
        with pytest.raises(Exception):
            social_account_repo.delete(db_session, fb_account.id, disconnect_test_user.id)

    # After rollback, the account should still exist in session
    db_session.rollback()
    existing = db_session.query(SocialAccount).filter(SocialAccount.id == fb_account.id).first()
    assert existing is not None
