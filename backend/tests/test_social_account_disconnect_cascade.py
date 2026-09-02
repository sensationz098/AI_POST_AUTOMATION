import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.external_post_context import ExternalPostContext
from app.repositories.social_account_repository import social_account_repo

def test_disconnect_social_account_cascades_external_post_contexts(db_session: Session):
    """
    Verify that disconnecting/deleting a SocialAccount:
    1. Successfully deletes the SocialAccount.
    2. Cascades and deletes all associated ExternalPostContexts.
    3. Does NOT throw a NotNullViolation or attempt to set social_account_id to NULL.
    4. Unrelated SocialAccounts and ExternalPostContexts remain untouched.
    """
    db = db_session
    # 1. Setup test user
    user = User(
        email="test_cascade_user@example.com",
        full_name="Test Cascade User",
        hashed_password="hashed_test_password",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Setup Social Account 1 (Target for disconnect)
    acc1 = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="page_11111",
        account_name="Test Page 1",
        access_token="tok_11111",
        status="CONNECTED"
    )
    # 3. Setup Social Account 2 (Unrelated account)
    acc2 = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="page_22222",
        account_name="Test Page 2",
        access_token="tok_22222",
        status="CONNECTED"
    )
    db.add_all([acc1, acc2])
    db.commit()
    db.refresh(acc1)
    db.refresh(acc2)

    # 4. Create ExternalPostContexts for Acc1
    ctx1 = ExternalPostContext(
        platform="facebook",
        social_account_id=acc1.id,
        external_post_id="post_111",
        caption="Caption 1"
    )
    ctx2 = ExternalPostContext(
        platform="facebook",
        social_account_id=acc1.id,
        external_post_id="post_112",
        caption="Caption 2"
    )

    # 5. Create ExternalPostContext for Acc2 (Unrelated)
    ctx3 = ExternalPostContext(
        platform="facebook",
        social_account_id=acc2.id,
        external_post_id="post_221",
        caption="Caption Unrelated"
    )
    db.add_all([ctx1, ctx2, ctx3])
    db.commit()
    db.refresh(ctx1)
    db.refresh(ctx2)
    db.refresh(ctx3)

    acc1_id = acc1.id
    acc2_id = acc2.id
    ctx1_id = ctx1.id
    ctx2_id = ctx2.id
    ctx3_id = ctx3.id

    # 6. Delete SocialAccount 1 via repository
    success = social_account_repo.delete(db, acc1_id, user.id)
    assert success is True

    # 7. Verify Acc1 and its dependent ExternalPostContexts (ctx1, ctx2) are completely removed
    assert db.query(SocialAccount).filter(SocialAccount.id == acc1_id).first() is None
    assert db.query(ExternalPostContext).filter(ExternalPostContext.id == ctx1_id).first() is None
    assert db.query(ExternalPostContext).filter(ExternalPostContext.id == ctx2_id).first() is None

    # 8. Verify Acc2 and its ExternalPostContext (ctx3) are completely unaffected
    remaining_acc2 = db.query(SocialAccount).filter(SocialAccount.id == acc2_id).first()
    remaining_ctx3 = db.query(ExternalPostContext).filter(ExternalPostContext.id == ctx3_id).first()

    assert remaining_acc2 is not None
    assert remaining_acc2.account_id == "page_22222"
    assert remaining_ctx3 is not None
    assert remaining_ctx3.social_account_id == acc2_id
    assert remaining_ctx3.external_post_id == "post_221"


def test_delete_all_for_user_cascades_external_post_contexts(db_session: Session):
    """
    Verify that delete_all_for_user safely removes all SocialAccounts and ExternalPostContexts.
    """
    db = db_session
    user = User(
        email="test_cascade_user2@example.com",
        full_name="Test Cascade User 2",
        hashed_password="hashed_test_password",
        is_active=True
    )
    db.add(user)
    db.commit()

    acc = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="page_33333",
        account_name="Test Page 3",
        access_token="tok_33333"
    )
    db.add(acc)
    db.commit()

    ctx = ExternalPostContext(
        platform="facebook",
        social_account_id=acc.id,
        external_post_id="post_333",
        caption="Caption 3"
    )
    db.add(ctx)
    db.commit()

    acc_id = acc.id
    deleted_count = social_account_repo.delete_all_for_user(db, user.id)
    assert deleted_count == 1

    assert db.query(SocialAccount).filter(SocialAccount.id == acc_id).first() is None
    assert db.query(ExternalPostContext).filter(ExternalPostContext.social_account_id == acc_id).first() is None
