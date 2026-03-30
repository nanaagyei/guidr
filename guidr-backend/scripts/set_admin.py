"""Script to set a user as admin by email."""
import sys
sys.path.insert(0, '.')

from sqlalchemy import text
from src.db import SessionLocal

def set_admin(email: str):
    """Set user role to admin by email."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email RETURNING id, email, role"),
            {"email": email}
        )
        updated = result.fetchone()
        db.commit()
        
        if updated:
            print(f"Successfully set user {updated.email} (id: {updated.id}) as admin")
        else:
            print(f"No user found with email: {email}")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Set the admin user
    set_admin("nanakwameagyeituffour@gmail.com")

