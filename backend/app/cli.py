import argparse
import sys
import logging
from app.core.database import SessionLocal
from app.core.security import get_password_hash, validate_password_strength
from app.models.user import User
from app.models.brand import BrandProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cli_bootstrap")

def bootstrap_admin(email: str, password: str, full_name: str):
    validate_password_strength(password)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.strip().lower()).first()
        if existing:
            logger.warning(f"User with email '{email}' already exists.")
            return

        admin_user = User(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            hashed_password=get_password_hash(password),
            role="Admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info(f"Successfully bootstrapped Admin account '{email}' (ID: {admin_user.id}).")

        # Create initial default Brand Profile for Admin
        brand = BrandProfile(
            name="Primary Brand",
            logo_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
            brand_colors=["#6366F1", "#06B6D4"],
            tone_of_voice="Professional & Engaging",
            target_audience="General Audience",
            cta_style="Value-focused",
            industry="Technology",
            user_id=admin_user.id
        )
        db.add(brand)
        db.commit()
        logger.info("Successfully created default Brand Profile.")
    except Exception as e:
        db.rollback()
        logger.error(f"Bootstrap failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap Administrator User")
    subparsers = parser.add_subparsers(dest="command")

    admin_parser = subparsers.add_parser("bootstrap-admin", help="Bootstrap initial Admin user")
    admin_parser.add_argument("--email", required=True, help="Admin email address")
    admin_parser.add_argument("--password", required=True, help="Admin password")
    admin_parser.add_argument("--name", default="System Admin", help="Admin full name")

    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        bootstrap_admin(args.email, args.password, args.name)
    else:
        parser.print_help()
