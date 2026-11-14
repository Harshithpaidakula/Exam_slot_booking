
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models

# Load JWT secret from .env
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY is missing in .env")

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30


# Create JWT after successful login
def create_access_token(user_id: int):

    expiry = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    data = {
        "user_id": str(user_id),
        "exp": expiry
    }

    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

    return token


# Verify JWT and identify the user
def get_user_from_token(token: str, db: Session):

    try:
        data = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(data["user_id"])

    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired login. Please log in again."
        )

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user or not user.isactive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive."
        )

    return user
