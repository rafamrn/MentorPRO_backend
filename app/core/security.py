# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_ALG = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(
    data: dict[str, Any],
    expires_minutes: int = 120,
    secret_key: str = "change-me",
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=SECRET_ALG)

def decode_token(token: str, secret_key: str) -> dict[str, Any]:
    return jwt.decode(token, secret_key, algorithms=[SECRET_ALG])
