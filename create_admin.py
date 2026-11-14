
import os

from dotenv import load_dotenv
from sqlalchemy import select

import database
from database import SessionLocal
import models
from utils import hash_password

load_dotenv()


def create_admin():
    database.create_tables()

    # Read credentials from .env
    name = os.getenv("ADMIN_NAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not all([name, email, password]):
        raise ValueError("Admin credentials missing in .env")

    with SessionLocal() as db:

        # Check whether an Admin already exists
        existing_admin = db.scalar(
            select(models.User).where(models.User.role == "Admin")
        )

        if existing_admin:
            print("Admin already exists!")
            return

        # Check whether this email is already registered
        existing_user = db.scalar(
            select(models.User).where(models.User.email == email)
        )

        if existing_user:
            raise ValueError("This email already belongs to another user")

        # Create Admin object
        admin = models.User(
            username=name,
            fullname=name,
            email=email,
            password_hash=hash_password(password),
            role="Admin",
            isactive=True,
        )

        # Save Admin in PostgreSQL
        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("Admin created successfully!")
        print("Admin ID:", admin.id)


if __name__ == "__main__":
    create_admin()

