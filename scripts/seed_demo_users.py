#!/usr/bin/env python3
"""
Create demo user accounts for all ITBIS roles.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password

DEMO_USERS = [
    {
        "full_name": "Admin User",
        "email": "admin@itbis.com",
        "password": "Password123!",
        "role": UserRole.ADMINISTRATOR,
    },
    {
        "full_name": "Security Manager",
        "email": "manager@itbis.com",
        "password": "Password123!",
        "role": UserRole.SECURITY_MANAGER,
    },
    {
        "full_name": "SOC Engineer",
        "email": "soc@itbis.com",
        "password": "Password123!",
        "role": UserRole.SOC_ENGINEER,
    },
    {
        "full_name": "Security Analyst",
        "email": "analyst@itbis.com",
        "password": "Password123!",
        "role": UserRole.SECURITY_ANALYST,
    },
]

def seed_users():
    db = SessionLocal()
    try:
        print("Seeding demo users...")
        for u in DEMO_USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                existing.hashed_password = hash_password(u["password"])
                existing.role = u["role"]
                existing.full_name = u["full_name"]
                print(f"  ✓ Updated existing user: {u['email']} ({u['role'].value})")
            else:
                new_user = User(
                    full_name=u["full_name"],
                    email=u["email"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    is_active=True,
                )
                db.add(new_user)
                print(f"  ✓ Created new user: {u['email']} ({u['role'].value})")
        db.commit()
        print("\nAll demo users created successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
