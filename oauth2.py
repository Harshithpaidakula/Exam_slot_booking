import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import models


# JWT learning flow:
# - create_access_token() makes a signed token after login.
# - get_user_from_token() checks that token on a protected page.
# - An expired or changed token is rejected.

# The secret key signs the token. Set JWT_SECRET_KEY in real deployments.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key")

# HS256 is the signing algorithm used for this small example.
ALGORITHM = "HS256"

# The token stops working after ten minutes.
ACCESS_TOKEN_EXPIRE_MINUTES = 10


# Create a JWT containing the user's database ID and an expiry time.
def create_access_token(user_id: int) -> str:
    # The expiry time makes the login temporary for better security.
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"user_id": str(user_id), "exp": expires}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)



# Decode the JWT and find the user it belongs to.
def get_user_from_token(token: str, db: Session) -> models.User:
    try:
        # decode() checks the signature and the expiry time for us.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["user_id"])
    except (JWTError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.isactive:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
