# auth_fastapi.py
import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-for-fastapi")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")) # 8 hours

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["scrypt", "bcrypt"], default="scrypt")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- OAuth2 Scheme ---
# This tells FastAPI where to look for the token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- JWT Token Handling ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- User Authentication ---
def get_user(db: Session, account: str) -> Optional[models.User]:
    """Retrieves a user from the database by their account name."""
    return db.query(models.User).filter(models.User.account == account).first()

def authenticate_user(db: Session, account: str, password: str) -> Optional[models.User]:
    """
    Authenticates a user. If successful, returns the user object.
    Otherwise, returns None.
    """
    user = get_user(db, account)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

# --- Dependencies ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Dependency to get the current user from a JWT token.
    Raises HTTPException if the token is invalid or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        account: str = payload.get("sub")
        if account is None:
            raise credentials_exception
        token_data = schemas.TokenData(account=account)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, account=token_data.account)
    if user is None:
        raise credentials_exception
    
    if not user.enabled:
        raise HTTPException(status_code=403, detail="User account is disabled")
        
    return user

def require_roles(required_roles: Tuple[str, ...]):
    """
    A dependency factory that returns a dependency to check for user roles.
    Example: `Depends(require_roles(("admin", "teacher")))`
    """
    def role_checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}.",
            )
        return current_user
    return role_checker
