import sys
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8 compatibility
sys.stdout.reconfigure(encoding='utf-8')

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv(os.path.join(backend_dir, '.env'))

from app.core.database import SessionLocal
from app.models.social_account import SocialAccount
from app.models.social_comment import SocialComment

def reconcile_instagram_comments():
    """
    Safe, idempotent one-time repair script to reconcile Instagram comments erroneously
    assigned to superseded SocialAccount id=24 (user_id=1) to the active SocialAccount id=39 (user_id=2)
    for external Instagram account 17841443294223730 (@blameless1802).
    """
    db = SessionLocal()
    try:
        print("=" * 70)
        print("ONE-TIME DATABASE RECONCILIATION: INSTAGRAM COMMENT OWNERSHIP")
        print("=" * 70)

        source_acc = db.query(SocialAccount).filter(SocialAccount.id == 24).first()
        target_acc = db.query(SocialAccount).filter(SocialAccount.id == 39).first()

        if not source_acc:
            print("Source account id=24 not found. Checking if comments already migrated.")
        if not target_acc:
            print("Target account id=39 not found. Aborting.")
            return

        print(f"Source Account: id={source_acc.id if source_acc else 'N/A'}, user_id={source_acc.user_id if source_acc else 'N/A'}, platform={source_acc.platform if source_acc else 'N/A'}, account_id={source_acc.account_id if source_acc else 'N/A'}, name={source_acc.account_name if source_acc else 'N/A'}")
        print(f"Target Account: id={target_acc.id}, user_id={target_acc.user_id}, platform={target_acc.platform}, account_id={target_acc.account_id}, name={target_acc.account_name}")
        print("-" * 70)

        # Query strictly scoped affected comments
        affected_comments = db.query(SocialComment).filter(
            SocialComment.social_account_id == 24,
            SocialComment.user_id == 1,
            SocialComment.platform == "instagram"
        ).order_by(SocialComment.id.asc()).all()

        count = len(affected_comments)
        print(f"Number of affected comments to reconcile: {count}")

        if count == 0:
            print("Zero comments currently require reconciliation. (Already reconciled or none present).")
            # Verify target comments count
            target_count = db.query(SocialComment).filter(
                SocialComment.social_account_id == 39,
                SocialComment.user_id == 2,
                SocialComment.platform == "instagram"
            ).count()
            print(f"Total comments currently owned by target account (id=39, user_id=2): {target_count}")
            return

        print("\nAffected comment details:")
        comment_ids = []
        for c in affected_comments:
            comment_ids.append(c.id)
            print(f"  Comment DB ID={c.id} | ext_id={c.external_comment_id} | ext_post_id={c.external_post_id} | commenter={c.commenter_name} | old_user_id={c.user_id} -> new_user_id={target_acc.user_id} | old_social_account_id={c.social_account_id} -> new_social_account_id={target_acc.id}")

        print(f"\nReconciling {count} comments [IDs: {comment_ids}]...")
        for c in affected_comments:
            c.user_id = target_acc.user_id
            c.social_account_id = target_acc.id
            c.updated_at = datetime.now(timezone.utc)

        db.commit()
        print("Reconciliation successfully committed.")

        # Verify
        recheck_source = db.query(SocialComment).filter(SocialComment.social_account_id == 24).count()
        recheck_target = db.query(SocialComment).filter(SocialComment.social_account_id == 39).count()
        print("-" * 70)
        print(f"Verification: Comments on SocialAccount 24 (user 1): {recheck_source}")
        print(f"Verification: Comments on SocialAccount 39 (user 2): {recheck_target}")
        print("=" * 70)
    except Exception as e:
        db.rollback()
        print(f"Error during reconciliation: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    reconcile_instagram_comments()
