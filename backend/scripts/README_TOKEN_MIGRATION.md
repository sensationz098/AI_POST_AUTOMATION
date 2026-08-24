# Meta Access Token Encryption Key Migration Guide

This utility safely migrates encrypted Meta access tokens stored in PostgreSQL (`social_accounts.access_token`) from the historical `SECRET_KEY`-derived Fernet key to the dedicated `TOKEN_ENCRYPTION_KEY`.

---

## 1. Safety Guarantees & Operating Constraints

- **DRY RUN is the DEFAULT**: Executing the script without `--apply` performs zero database writes.
- **Single Transaction**: In `--apply` mode, all database updates occur inside one atomic transaction. Any error or decryption failure triggers an immediate rollback.
- **Idempotent**: Tokens already encrypted with `TOKEN_ENCRYPTION_KEY` are detected automatically and skipped without re-encryption or corruption.
- **Strict Key Validation**: If `TOKEN_ENCRYPTION_KEY` is missing or invalid, the process aborts immediately. Fallback to `SECRET_KEY` for the new key is strictly forbidden.
- **No Secret Leakage**: Plaintext tokens, `SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, and database credentials are never printed, logged, or stored.
- **Zero API Side Effects**: Never makes calls to Meta Graph APIs or reconnects social accounts.

---

## 2. Required Environment Variables

Ensure the following environment variables are set in your environment or `.env` file before running the script:

- `SECRET_KEY`: Historical application secret key used to derive the old Fernet key.
- `TOKEN_ENCRYPTION_KEY`: The newly generated valid Fernet key (44-character url-safe base64 string or 32+ character key).
- `DATABASE_URL`: PostgreSQL connection string (e.g. `postgresql+psycopg://user:pass@host:5432/dbname`).

---

## 3. Exact Commands

### A. Dry Run (Read-Only Inspection)

Run the script without `--apply` (or explicitly pass `--dry-run` if desired). This checks all records and outputs a safe metadata report without making any database changes.

```bash
python backend/scripts/migrate_token_encryption.py
```

### B. Apply Mode (Persists Changes to Production DB)

When the dry-run output is verified and zero failures are reported, pass the `--apply` flag to commit the re-encrypted tokens to the database.

```bash
python backend/scripts/migrate_token_encryption.py --apply
```

---

## 4. Expected Output Format

### Dry Run Output Example:

```text
2026-08-24 12:00:00 [INFO] === Starting Meta Token Encryption Migration [DRY RUN (READ-ONLY)] ===
2026-08-24 12:00:00 [INFO] OLD Fernet key successfully derived from SECRET_KEY.
2026-08-24 12:00:00 [INFO] NEW Fernet key successfully validated from TOKEN_ENCRYPTION_KEY.
2026-08-24 12:00:00 [INFO] Found 9 social_accounts record(s) matching access_token pattern 'enc_gAAAAA%'.

==========================================================================================
SAFE METADATA REPORT [DRY RUN (READ-ONLY)]
==========================================================================================
ID     | Platform     | Account ID           | Old Decrypt               | New Encrypt               | New Verify
------------------------------------------------------------------------------------------
1      | facebook     | 1092837465102938     | SUCCESS                   | SUCCESS                   | SUCCESS   
2      | instagram    | 1784140192837465     | SUCCESS                   | SUCCESS                   | SUCCESS   
...
==========================================================================================

2026-08-24 12:00:00 [INFO] Summary: 9 total account(s) checked | 0 already migrated | 9 ready to migrate.
2026-08-24 12:00:00 [INFO] DRY RUN COMPLETE: All checks passed! ZERO database modifications were made.
2026-08-24 12:00:00 [INFO] To apply these changes to the database, run with: python backend/scripts/migrate_token_encryption.py --apply
```

---

## 5. How Already-Migrated Tokens Are Detected

When inspecting a record whose token starts with `enc_gAAAAA`:
1. The script first attempts to decrypt the token using `TOKEN_ENCRYPTION_KEY`.
2. If decryption succeeds, the token is recognized as **already migrated** to the new key.
3. The script marks the record status as `SKIPPED (ALREADY_MIGRATED)` and leaves the database record untouched, preventing double-encryption or corruption.
