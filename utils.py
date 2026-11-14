# These functions protect passwords before saving and checking them.
from passlib.context import CryptContext


# Passlib creates and checks password hashes.
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
)


def hash_password(password: str):
    # Convert a plain password into a safe hash.
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    # Check a plain password against a saved hash.
    return pwd_context.verify(plain_password, hashed_password)
