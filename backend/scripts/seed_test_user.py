#!/usr/bin/env python3
"""
Seed Test User Script for AI Post Automation Platform
Creates or updates the default test user in PostgreSQL.
"""

import sys
import os

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.repositories.user_repository import user_repo
from app.core.security import get_password_hash

TEST_USER_EMAIL = "testadmin@socialai.com"
TEST_USER_PASSWORD = "TestAdmin123!"
TEST_USER_NAME = "Test Administrator"
TEST_USER_ROLE = "Admin"

def seed_test_user():
    db = SessionLocal()
    try:
        existing = user_repo.get_by_email(db, TEST_USER_EMAIL)
        hashed_pwd = get_password_hash(TEST_USER_PASSWORD)
        
        if existing:
            user_repo.update(db, db_obj=existing, obj_in={
                "hashed_password": hashed_pwd,
                "full_name": TEST_USER_NAME,
                "role": TEST_USER_ROLE,
                "is_active": True
            })
            print(f"Updated existing test user: {TEST_USER_EMAIL}")
        else:
            user_repo.create(db, obj_in={
                "email": TEST_USER_EMAIL,
                "hashed_password": hashed_pwd,
                "full_name": TEST_USER_NAME,
                "role": TEST_USER_ROLE,
                "is_active": True
            })
            print(f"Created new test user: {TEST_USER_EMAIL}")
            
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_user()
