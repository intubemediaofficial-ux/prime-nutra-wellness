from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order
from ..utils import get_settings

router = APIRouter(prefix="/api/payments", tags=["payments"])


class CreatePayIn(BaseModel):
    order_id: str


class VerifyIn(BaseModel):
    order_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.get("/config")
def pay_config(db: Session = Depends(get_db)):
    s = get_settings(db)
    return {
        "razorpay_enabled": s.get("razorpay_enabled") == "true" and bool(s.get("razorpay_key_id")),
        "razorpay_key_id": s.get("razorpay_key_id", ""),
        "cod_enabled": s.get("cod_enabled", "true") == "true",
        "currency": "INR",
    }


@router.post("/razorpay/create")
def create_razorpay_order(data: CreatePayIn, db: Session = Depends(get_db)):
    s = get_settings(db)
    if s.get("razorpay_enabled") != "true" or not s.get("razorpay_key_id") or not s.get("razorpay_key_secret"):
        raise HTTPException(status_code=400, detail="Razorpay is not configured")
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    import razorpay

    client = razorpay.Client(auth=(s["razorpay_key_id"], s["razorpay_key_secret"]))
    rp_order = client.order.create({
        "amount": int(round(order.total * 100)),  # paise
        "currency": "INR",
        "receipt": order.id,
        "notes": {"order_id": order.id},
    })
    order.razorpay_order_id = rp_order["id"]
    order.payment_method = "Razorpay"
    db.commit()
    return {
        "razorpay_order_id": rp_order["id"],
        "amount": rp_order["amount"],
        "currency": rp_order["currency"],
        "key_id": s["razorpay_key_id"],
    }


@router.post("/razorpay/verify")
def verify_razorpay(data: VerifyIn, db: Session = Depends(get_db)):
    s = get_settings(db)
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    import razorpay

    client = razorpay.Client(auth=(s["razorpay_key_id"], s["razorpay_key_secret"]))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        order.payment_status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Payment verification failed")

    order.payment_status = "paid"
    order.razorpay_payment_id = data.razorpay_payment_id
    order.status = "confirmed"
    db.commit()
    return {"ok": True, "payment_status": "paid"}
