"""Auth helpers — JWT for admin + customer, bcrypt for admin passwords."""
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_HOURS, SECRET_KEY
from .database import get_db
from .models import AdminUser, Customer

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login", auto_error=False)
customer_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/otp/verify", auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire, "type": "admin"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_customer_token(customer_id: int, phone: str) -> str:
    expire = datetime.utcnow() + timedelta(days=30)
    payload = {"sub": str(customer_id), "phone": phone, "exp": expire, "type": "customer"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AdminUser:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if payload.get("type") not in (None, "admin"):
            raise cred_exc
    except jwt.PyJWTError:
        raise cred_exc
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not user:
        raise cred_exc
    return user


def get_current_customer(
    token: str = Depends(customer_oauth2), db: Session = Depends(get_db)
) -> Customer:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "customer":
            raise cred_exc
        customer_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError):
        raise cred_exc
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer or not customer.is_active:
        raise cred_exc
    return customer


def get_optional_customer(
    token: str = Depends(customer_oauth2), db: Session = Depends(get_db)
) -> Customer | None:
    """Return customer if token is valid, else None (no error)."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "customer":
            return None
        customer_id = int(payload.get("sub", 0))
    except (jwt.PyJWTError, ValueError):
        return None
    return db.query(Customer).filter(Customer.id == customer_id, Customer.is_active == True).first()
