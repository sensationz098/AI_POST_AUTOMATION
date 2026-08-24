#!/usr/bin/env python3
"""
Token Encryption Migration Utility
==================================

Migrates encrypted Meta access tokens stored in `social_accounts.access_token`
from the historical SECRET_KEY-derived Fernet key to the dedicated TOKEN_ENCRYPTION_KEY.

Usage:
    Dry Run (Default, ZERO database changes):
        python backend/scripts/migrate_token_encryption.py

    Apply Mode (Executes database transaction):
        python backend/scripts/migrate_token_encryption.py --apply

Environment Variables Required:
    - SECRET_KEY: The application secret key used for historical key derivation.
    - TOKEN_ENCRYPTION_KEY: The newly generated Fernet key.
    - DATABASE_URL (or POSTGRES_* settings): Database connection string.
"""

import argparse
import base64
import hashlib
import logging
import os
import sys
from typing import List, Dict, Any

# Ensure backend folder is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables from backend/.env or current working directory
from dotenv import load_dotenv
backend_env_path = os.path.join(backend_dir, ".env")
if os.path.exists(backend_env_path):
    load_dotenv(backend_env_path)
load_dotenv()

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.social_account import SocialAccount

# Set up clean logging format
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_token_encryption")


def derive_old_fernet(secret_key: str) -> Fernet:
    """
    Recreates the historical Fernet key derived from SECRET_KEY.
    Algorithm: hashlib.sha256(SECRET_KEY.encode('utf-8')).digest() -> base64.urlsafe_b64encode -> Fernet
    """
    if not secret_key or not secret_key.strip():
        raise ValueError("SECRET_KEY is missing or empty. Cannot recreate historical key.")
    key_bytes = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode("utf-8")).digest())
    return Fernet(key_bytes)


def get_new_fernet(token_encryption_key: str) -> Fernet:
    """
    Validates and instantiates the Fernet key derived from TOKEN_ENCRYPTION_KEY.
    Strictly forbids falling back to SECRET_KEY for the new key.
    """
    if not token_encryption_key or not token_encryption_key.strip():
        raise ValueError(
            "CRITICAL: TOKEN_ENCRYPTION_KEY is missing or empty. "
            "Migration cannot proceed. Never fall back to SECRET_KEY for the new key."
        )

    key_str = token_encryption_key.strip()

    try:
        if len(key_str) == 44 and key_str.endswith("="):
            f = Fernet(key_str.encode("utf-8"))
        elif len(key_str) >= 32:
            key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key_str.encode("utf-8")).digest())
            f = Fernet(key_bytes)
        else:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be a valid 44-character Fernet key or at least 32 characters long.")

        # Operational validation test
        test_payload = b"token_migration_test_payload"
        enc_test = f.encrypt(test_payload)
        if f.decrypt(enc_test) != test_payload:
            raise ValueError("Encryption test decrypt mismatch.")

        return f
    except Exception as e:
        raise ValueError(f"CRITICAL: TOKEN_ENCRYPTION_KEY validation failed: {e}")


def inspect_and_migrate_account(
    account: SocialAccount,
    old_fernet: Fernet,
    new_fernet: Fernet
) -> Dict[str, Any]:
    """
    Performs key check, decryption, re-encryption, and verification on a single SocialAccount record.
    Returns safe metadata without exposing plaintext tokens or key materials.
    """
    meta: Dict[str, Any] = {
        "id": account.id,
        "platform": account.platform,
        "account_id": account.account_id,
        "old_decryption": "FAILED",
        "new_encryption": "FAILED",
        "new_verification": "FAILED",
        "already_migrated": False,
        "new_token": None,
        "error": None,
    }

    token_val = account.access_token
    if not token_val or not token_val.startswith("enc_gAAAAA"):
        meta["error"] = "Invalid token prefix (expected 'enc_gAAAAA')"
        return meta

    raw_ciphertext = token_val[4:].encode("utf-8")

    # Step 1: Idempotency check - test if ALREADY migrated with new_fernet
    try:
        dec_bytes = new_fernet.decrypt(raw_ciphertext)
        # Decryption with new key succeeded! Account is already migrated.
        meta["old_decryption"] = "SKIPPED (ALREADY_MIGRATED)"
        meta["new_encryption"] = "SKIPPED (ALREADY_MIGRATED)"
        meta["new_verification"] = "SUCCESS"
        meta["already_migrated"] = True
        return meta
    except InvalidToken:
        # Not encrypted with new key; proceed with migration using old key
        pass
    except Exception:
        pass

    # Step 2: Decrypt using OLD key
    try:
        plain_bytes = old_fernet.decrypt(raw_ciphertext)
        meta["old_decryption"] = "SUCCESS"
    except InvalidToken:
        meta["old_decryption"] = "FAILED (InvalidToken)"
        meta["error"] = "Token decryption failed with OLD key (token corrupt or key mismatch)."
        return meta
    except Exception as e:
        meta["old_decryption"] = f"FAILED ({type(e).__name__})"
        meta["error"] = f"Token decryption failed with OLD key: {e}"
        return meta

    # Step 3: Encrypt using NEW key
    try:
        new_enc_bytes = new_fernet.encrypt(plain_bytes)
        new_token_str = f"enc_{new_enc_bytes.decode('utf-8')}"
        meta["new_encryption"] = "SUCCESS"
        meta["new_token"] = new_token_str
    except Exception as e:
        meta["new_encryption"] = f"FAILED ({type(e).__name__})"
        meta["error"] = f"Token re-encryption failed with NEW key: {e}"
        return meta

    # Step 4: Verify newly encrypted token using NEW key internally
    try:
        verify_raw = new_token_str[4:].encode("utf-8")
        verify_bytes = new_fernet.decrypt(verify_raw)
        if verify_bytes == plain_bytes:
            meta["new_verification"] = "SUCCESS"
        else:
            meta["new_verification"] = "FAILED (Mismatch)"
            meta["error"] = "Internal verification failed: re-encrypted token decrypted to different payload."
    except Exception as e:
        meta["new_verification"] = f"FAILED ({type(e).__name__})"
        meta["error"] = f"Internal verification failed: {e}"

    return meta


def run_migration(apply: bool = False, db_session: Session = None) -> bool:
    """
    Main migration runner.
    If apply=False (default), performs a DRY RUN with zero database writes.
    If apply=True, executes the migration in a single database transaction.
    """
    mode_str = "APPLY (DATABASE MUTATION)" if apply else "DRY RUN (READ-ONLY)"
    logger.info(f"=== Starting Meta Token Encryption Migration [{mode_str}] ===")

    # 1. Recreate OLD Fernet key
    try:
        old_fernet = derive_old_fernet(settings.SECRET_KEY)
        logger.info("OLD Fernet key successfully derived from SECRET_KEY.")
    except Exception as e:
        logger.error(f"Failed to derive OLD Fernet key: {e}")
        return False

    # 2. Validate NEW Fernet key
    try:
        new_fernet = get_new_fernet(settings.TOKEN_ENCRYPTION_KEY or "")
        logger.info("NEW Fernet key successfully validated from TOKEN_ENCRYPTION_KEY.")
    except Exception as e:
        logger.error(f"NEW Fernet key validation failed: {e}")
        return False

    close_session = False
    if db_session is None:
        db_session = SessionLocal()
        close_session = True

    try:
        # 3. Query all social_accounts records with access_token starting with 'enc_gAAAAA'
        accounts = db_session.query(SocialAccount).filter(
            SocialAccount.access_token.like("enc_gAAAAA%")
        ).all()

        logger.info(f"Found {len(accounts)} social_accounts record(s) matching access_token pattern 'enc_gAAAAA%'.")

        if not accounts:
            logger.info("No social_accounts records found for migration.")
            return True

        processed_results: List[Dict[str, Any]] = []
        has_failures = False

        for acc in accounts:
            res = inspect_and_migrate_account(acc, old_fernet, new_fernet)
            processed_results.append(res)
            if res["error"] or res["new_verification"] != "SUCCESS":
                has_failures = True

        # Print Safe Metadata Report
        print("\n" + "=" * 90)
        print(f"SAFE METADATA REPORT [{mode_str}]")
        print("=" * 90)
        header = f"{'ID':<6} | {'Platform':<12} | {'Account ID':<20} | {'Old Decrypt':<25} | {'New Encrypt':<25} | {'New Verify':<10}"
        print(header)
        print("-" * len(header))

        for r in processed_results:
            row_str = f"{r['id']:<6} | {r['platform']:<12} | {r['account_id']:<20} | {r['old_decryption']:<25} | {r['new_encryption']:<25} | {r['new_verification']:<10}"
            print(row_str)
            if r["error"]:
                print(f"  └─ ERROR: {r['error']}")
        print("=" * 90 + "\n")

        if has_failures:
            logger.error("MIGRATION ABORTED: One or more accounts failed decryption/verification.")
            if apply:
                db_session.rollback()
                logger.info("Database transaction rolled back cleanly. ZERO changes persisted.")
            return False

        already_migrated_count = sum(1 for r in processed_results if r["already_migrated"])
        to_migrate_count = len(processed_results) - already_migrated_count

        logger.info(f"Summary: {len(processed_results)} total account(s) checked | {already_migrated_count} already migrated | {to_migrate_count} ready to migrate.")

        if not apply:
            logger.info("DRY RUN COMPLETE: All checks passed! ZERO database modifications were made.")
            logger.info("To apply these changes to the database, run with: python backend/scripts/migrate_token_encryption.py --apply")
            return True

        # APPLY mode: execute single transaction update
        logger.info("APPLY MODE: Persisting updated tokens to database in a single transaction...")
        for r in processed_results:
            if not r["already_migrated"]:
                acc_obj = db_session.query(SocialAccount).filter(SocialAccount.id == r["id"]).first()
                if acc_obj:
                    acc_obj.access_token = r["new_token"]

        db_session.commit()
        logger.info("MIGRATION SUCCESSFUL: All access tokens successfully re-encrypted and persisted!")
        return True

    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        if apply:
            db_session.rollback()
            logger.info("Database transaction rolled back due to error. ZERO changes persisted.")
        return False
    finally:
        if close_session:
            db_session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate encrypted Meta access tokens from historical SECRET_KEY to TOKEN_ENCRYPTION_KEY."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes to the database. If omitted, default DRY RUN (read-only) mode is executed."
    )
    args = parser.parse_args()

    success = run_migration(apply=args.apply)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
