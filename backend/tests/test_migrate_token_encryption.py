import pytest
import base64
import hashlib
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.social_account import SocialAccount
from app.core.config import settings
from scripts.migrate_token_encryption import (
    derive_old_fernet,
    get_new_fernet,
    inspect_and_migrate_account,
    run_migration,
)


@pytest.fixture
def keys():
    secret_key = "test_secret_key_for_migration_test_12345"
    token_encryption_key = Fernet.generate_key().decode("utf-8")
    
    old_fernet = derive_old_fernet(secret_key)
    new_fernet = get_new_fernet(token_encryption_key)
    
    return {
        "secret_key": secret_key,
        "token_encryption_key": token_encryption_key,
        "old_fernet": old_fernet,
        "new_fernet": new_fernet,
    }


def test_key_derivation_and_validation(keys):
    """Verify historical key derivation and new key validation functions."""
    # Historical key derivation from secret key
    old_f = derive_old_fernet(keys["secret_key"])
    assert isinstance(old_f, Fernet)
    
    # Valid new key
    new_f = get_new_fernet(keys["token_encryption_key"])
    assert isinstance(new_f, Fernet)

    # Missing or empty TOKEN_ENCRYPTION_KEY must fail fast
    with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY is missing or empty"):
        get_new_fernet("")
    
    with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY is missing or empty"):
        get_new_fernet("   ")

    # Invalid key length (<32 characters and not 44-char Fernet key) must fail validation
    with pytest.raises(ValueError, match="validation failed"):
        get_new_fernet("too_short_key")


def test_dry_run_performs_zero_database_modifications(db_session: Session, keys, monkeypatch):
    """Verify that dry run evaluates tokens, reports safe metadata, but makes ZERO DB changes."""
    monkeypatch.setattr(settings, "SECRET_KEY", keys["secret_key"])
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", keys["token_encryption_key"])

    # Create dummy user
    user = User(email="test_dryrun@example.com", hashed_password="hashed", full_name="DryRun Test")
    db_session.add(user)
    db_session.commit()

    # Create account with token encrypted using OLD key
    plain_token = "EAAB1234567890_test_token_dryrun"
    old_enc_bytes = keys["old_fernet"].encrypt(plain_token.encode("utf-8"))
    old_token_str = f"enc_{old_enc_bytes.decode('utf-8')}"

    acc = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="1001",
        account_name="DryRun Page",
        access_token=old_token_str,
    )
    db_session.add(acc)
    db_session.commit()

    # Execute DRY RUN
    success = run_migration(apply=False, db_session=db_session)
    assert success is True

    # Refresh record from DB to verify access_token was UNCHANGED
    db_session.refresh(acc)
    assert acc.access_token == old_token_str


def test_apply_mode_migrates_tokens_successfully(db_session: Session, keys, monkeypatch):
    """Verify that --apply updates access_token in DB and allows decryption with NEW key."""
    monkeypatch.setattr(settings, "SECRET_KEY", keys["secret_key"])
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", keys["token_encryption_key"])

    user = User(email="test_apply@example.com", hashed_password="hashed", full_name="Apply Test")
    db_session.add(user)
    db_session.commit()

    plain_token = "EAAB9876543210_test_token_apply"
    old_enc_bytes = keys["old_fernet"].encrypt(plain_token.encode("utf-8"))
    old_token_str = f"enc_{old_enc_bytes.decode('utf-8')}"

    acc = SocialAccount(
        user_id=user.id,
        platform="instagram",
        account_id="2002",
        account_name="Apply IG",
        access_token=old_token_str,
    )
    db_session.add(acc)
    db_session.commit()

    # Execute APPLY mode
    success = run_migration(apply=True, db_session=db_session)
    assert success is True

    # Refresh record from DB
    db_session.refresh(acc)
    assert acc.access_token != old_token_str
    assert acc.access_token.startswith("enc_gAAAAA")

    # Verify new token decrypts with NEW fernet key
    new_raw = acc.access_token[4:].encode("utf-8")
    decrypted_plain = keys["new_fernet"].decrypt(new_raw).decode("utf-8")
    assert decrypted_plain == plain_token


def test_idempotency_already_migrated_tokens(db_session: Session, keys, monkeypatch):
    """Verify that running migration on already-migrated tokens detects them and avoids double-encryption."""
    monkeypatch.setattr(settings, "SECRET_KEY", keys["secret_key"])
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", keys["token_encryption_key"])

    user = User(email="test_idempotent@example.com", hashed_password="hashed", full_name="Idempotent Test")
    db_session.add(user)
    db_session.commit()

    plain_token = "EAAB55555_already_migrated"
    new_enc_bytes = keys["new_fernet"].encrypt(plain_token.encode("utf-8"))
    already_migrated_token = f"enc_{new_enc_bytes.decode('utf-8')}"

    acc = SocialAccount(
        user_id=user.id,
        platform="facebook",
        account_id="3003",
        account_name="Migrated Page",
        access_token=already_migrated_token,
    )
    db_session.add(acc)
    db_session.commit()

    # Run inspection directly
    meta = inspect_and_migrate_account(acc, keys["old_fernet"], keys["new_fernet"])
    assert meta["already_migrated"] is True
    assert meta["old_decryption"] == "SKIPPED (ALREADY_MIGRATED)"
    assert meta["new_encryption"] == "SKIPPED (ALREADY_MIGRATED)"
    assert meta["new_verification"] == "SUCCESS"

    # Run migration in apply mode
    success = run_migration(apply=True, db_session=db_session)
    assert success is True

    # Token in DB must remain unchanged
    db_session.refresh(acc)
    assert acc.access_token == already_migrated_token


def test_corrupt_token_aborts_migration_and_rolls_back(db_session: Session, keys, monkeypatch):
    """Verify that if ANY token fails decryption with old key, migration aborts and rolls back."""
    monkeypatch.setattr(settings, "SECRET_KEY", keys["secret_key"])
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", keys["token_encryption_key"])

    user = User(email="test_corrupt@example.com", hashed_password="hashed", full_name="Corrupt Test")
    db_session.add(user)
    db_session.commit()

    # Valid old token
    plain1 = "EAAB111_valid"
    old_enc1 = f"enc_{keys['old_fernet'].encrypt(plain1.encode('utf-8')).decode('utf-8')}"

    # Corrupted old token (encrypted with random key)
    other_fernet = Fernet(Fernet.generate_key())
    corrupt_enc = f"enc_{other_fernet.encrypt(b'corrupt').decode('utf-8')}"

    acc1 = SocialAccount(user_id=user.id, platform="facebook", account_id="4001", account_name="P1", access_token=old_enc1)
    acc2 = SocialAccount(user_id=user.id, platform="instagram", account_id="4002", account_name="P2", access_token=corrupt_enc)
    db_session.add_all([acc1, acc2])
    db_session.commit()

    # Run migration in apply mode -> must fail
    success = run_migration(apply=True, db_session=db_session)
    assert success is False

    # Verify acc1 was NOT updated due to transaction rollback
    db_session.refresh(acc1)
    assert acc1.access_token == old_enc1
