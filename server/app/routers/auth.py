from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import AdminUser
from ..schemas import LoginIn, PasswordChange, TokenOut

router = APIRouter(prefix="/api/admin", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user.username)
    return TokenOut(access_token=token, username=user.username)


@router.get("/me")
def me(admin: AdminUser = Depends(get_current_admin)):
    return {"username": admin.username, "role": admin.role}


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    admin.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}
