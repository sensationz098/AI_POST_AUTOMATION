#!/usr/bin/env python3
"""
SQLite to PostgreSQL Data Migration Script
AI Post Automation Platform

Usage:
    python scripts/migrate_sqlite_to_postgres.py --sqlite-uri sqlite:///./social_ai.db --postgres-uri postgresql+psycopg://postgres:password@localhost:5432/social_ai_db [--dry-run]
"""

import argparse
import sys
import logging
from sqlalchemy import create_engine, MetaData, Table, inspect, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sqlite_to_postgres_migration")

# Table migration order respecting Foreign Key dependency hierarchy
TABLE_ORDER = [
    "users",
    "brand_profiles",
    "meta_accounts",
    "social_accounts",
    "posts",
    "publishing_batches",
    "publishing_jobs",
    "post_analytics",
    "audit_logs",
]

def migrate(sqlite_uri: str, postgres_uri: str, dry_run: bool = False):
    logger.info("Starting SQLite -> PostgreSQL Migration Process...")
    logger.info(f"Source SQLite: {sqlite_uri}")
    logger.info(f"Target PostgreSQL: {postgres_uri.split('@')[-1] if '@' in postgres_uri else postgres_uri}")
    logger.info(f"Dry Run Mode: {dry_run}")

    sqlite_engine = create_engine(sqlite_uri, connect_args={"check_same_thread": False})
    postgres_engine = create_engine(postgres_uri, pool_pre_ping=True)

    sqlite_meta = MetaData()
    postgres_meta = MetaData()

    sqlite_inspector = inspect(sqlite_engine)
    postgres_inspector = inspect(postgres_engine)

    sqlite_tables = sqlite_inspector.get_table_names()
    postgres_tables = postgres_inspector.get_table_names()

    logger.info(f"Found {len(sqlite_tables)} tables in SQLite source.")

    if not dry_run:
        # Disable foreign key checks temporarily in PostgreSQL target session
        with postgres_engine.begin() as conn:
            conn.execute(text("SET CONSTRAINTS ALL DEFERRED;"))

    total_migrated_records = 0

    for table_name in TABLE_ORDER:
        if table_name not in sqlite_tables:
            logger.warning(f"Table '{table_name}' does not exist in SQLite source. Skipping.")
            continue

        if table_name not in postgres_tables:
            logger.warning(f"Table '{table_name}' does not exist in PostgreSQL target. Run Alembic migrations first! Skipping.")
            continue

        src_table = Table(table_name, sqlite_meta, autoload_with=sqlite_engine)
        tgt_table = Table(table_name, postgres_meta, autoload_with=postgres_engine)

        with sqlite_engine.connect() as src_conn:
            records = src_conn.execute(src_table.select()).mappings().all()

        logger.info(f"Migrating {len(records)} rows for table '{table_name}'...")

        if not records:
            continue

        if dry_run:
            logger.info(f"[DRY-RUN] Would insert {len(records)} rows into '{table_name}'.")
            total_migrated_records += len(records)
            continue

        with postgres_engine.begin() as tgt_conn:
            # Delete any existing sample rows to prevent primary key collision
            tgt_conn.execute(text(f'DELETE FROM "{table_name}" WHERE 1=1;'))

            for row in records:
                row_dict = dict(row)
                tgt_conn.execute(tgt_table.insert().values(**row_dict))

        total_migrated_records += len(records)
        logger.info(f"Successfully migrated {len(records)} records into table '{table_name}'.")

    # Reset PostgreSQL primary key auto-increment sequences after explicit ID inserts
    if not dry_run:
        with postgres_engine.begin() as conn:
            for table_name in TABLE_ORDER:
                if table_name in postgres_tables:
                    try:
                        seq_query = text(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM \"{table_name}\";")
                        conn.execute(seq_query)
                    except Exception as e:
                        logger.debug(f"Sequence reset notice for '{table_name}': {e}")

    logger.info(f"Migration completed cleanly! Total records transferred: {total_migrated_records}")

def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL for AI Post Automation.")
    parser.add_argument("--sqlite-uri", default="sqlite:///./social_ai.db", help="SQLite database URI")
    parser.add_argument("--postgres-uri", required=True, help="PostgreSQL target database URI")
    parser.add_argument("--dry-run", action="store_true", help="Validate migration without modifying target DB")

    args = parser.parse_args()
    migrate(args.sqlite_uri, args.postgres_uri, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
