from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, Coupon
from ..schemas import CouponIn, SettingsIn
from ..utils import SECRET_SETTING_KEYS, get_settings, set_setting

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- Settings ----------
@router.get("/settings")
def read_settings(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    s = get_settings(db)
    # mask secret values but indicate whether they're set
    out = dict(s)
    for k in SECRET_SETTING_KEYS:
        out[k + "_set"] = bool(s.get(k))
        out[k] = ""  # never echo secret back
    return out


@router.put("/settings")
def update_settings(
    data: SettingsIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    for k, v in data.values.items():
        # skip empty secret values so we don't wipe existing secrets accidentally
        if k in SECRET_SETTING_KEYS and (v is None or v == ""):
            continue
        set_setting(db, k, "" if v is None else str(v))
    db.commit()
    return {"ok": True}


# ---------- Coupons ----------
@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return db.query(Coupon).all()


@router.post("/coupons")
def upsert_coupon(
    data: CouponIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    code = data.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Coupon code required")
    c = db.query(Coupon).filter(Coupon.code == code).first()
    if not c:
        c = Coupon(code=code)
        db.add(c)
    c.type = data.type
    c.value = data.value
    c.min_order = data.min_order
    c.active = data.active
    c.expires_at = data.expires_at
    db.commit()
    return {"ok": True, "code": code}


@router.delete("/coupons/{code}")
def delete_coupon(
    code: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    c = db.query(Coupon).filter(Coupon.code == code.upper()).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}
