"""Customer OTP-based authentication — send OTP, verify, profile."""
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_customer_token, get_current_customer
from ..database import get_db
from ..models import Customer, OTP
from ..schemas import (
    AddressIn,
    AddressOut,
    CustomerProfileIn,
    CustomerTokenOut,
    OTPSendIn,
    OTPVerifyIn,
)
from ..models import Address
from ..utils import get_settings

router = APIRouter(prefix="/api/auth", tags=["customer-auth"])


def _generate_otp() -> str:
    return str(random.randint(100000, 999999))


def _send_otp_sms(phone: str, code: str, settings: dict) -> bool:
    """Send OTP via configured provider. Returns True if sent."""
    provider = settings.get("otp_provider", "console")
    if provider == "console":
        print(f"[OTP] {phone} → {code}")
        return True
    if provider == "msg91":
        import requests
        api_key = settings.get("otp_api_key", "")
        if not api_key:
            return False
        try:
            resp = requests.post(
                "https://api.msg91.com/api/v5/otp",
                headers={"authkey": api_key},
                json={"mobile": phone, "otp": code, "sender": settings.get("otp_sender_id", "PNWOTP")},
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False
    if provider == "twilio":
        try:
            from twilio.rest import Client
            api_key = settings.get("otp_api_key", "")
            parts = api_key.split("|")
            if len(parts) < 3:
                return False
            client = Client(parts[0], parts[1])
            client.messages.create(
                body=f"Your PrimeNutra Wellness OTP is: {code}",
                from_=parts[2],
                to=f"+{phone}" if not phone.startswith("+") else phone,
            )
            return True
        except Exception:
            return False
    return False


@router.post("/otp/send")
def send_otp(data: OTPSendIn, db: Session = Depends(get_db)):
    phone = data.phone.strip().replace("+", "").replace(" ", "")
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    # Rate limit: max 5 OTPs per phone in 10 mins
    ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
    recent = db.query(OTP).filter(OTP.phone == phone, OTP.created_at >= ten_min_ago).count()
    if recent >= 5:
        raise HTTPException(status_code=429, detail="Too many OTP requests. Try again later.")

    code = _generate_otp()
    otp = OTP(
        phone=phone,
        code=code,
        purpose="login",
        expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    db.add(otp)
    db.commit()

    settings = get_settings(db)
    sent = _send_otp_sms(phone, code, settings)

    return {
        "ok": True,
        "message": "OTP sent successfully" if sent else "OTP generated (check console for dev mode)",
        "phone": phone,
        # In dev/console mode, return OTP for testing
        **({"otp": code} if settings.get("otp_provider") == "console" else {}),
    }


@router.post("/otp/verify", response_model=CustomerTokenOut)
def verify_otp(data: OTPVerifyIn, db: Session = Depends(get_db)):
    phone = data.phone.strip().replace("+", "").replace(" ", "")
    code = data.code.strip()

    otp = (
        db.query(OTP)
        .filter(OTP.phone == phone, OTP.verified == False, OTP.expires_at >= datetime.utcnow())
        .order_by(OTP.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    otp.attempts += 1
    if otp.attempts > 5:
        raise HTTPException(status_code=429, detail="Too many attempts")

    if otp.code != code:
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp.verified = True
    db.commit()

    # Find or create customer
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    is_new = False
    if not customer:
        customer = Customer(phone=phone)
        db.add(customer)
        db.commit()
        db.refresh(customer)
        is_new = True

    token = create_customer_token(customer.id, customer.phone)
    return CustomerTokenOut(
        access_token=token,
        customer_id=customer.id,
        phone=customer.phone,
        name=customer.name or "",
        is_new=is_new,
    )


# ───────────────────────────── Profile ─────────────────────────────

@router.get("/profile")
def get_profile(customer: Customer = Depends(get_current_customer)):
    return {
        "id": customer.id,
        "phone": customer.phone,
        "name": customer.name,
        "email": customer.email,
        "gst_number": customer.gst_number,
        "created_at": customer.created_at.isoformat() if customer.created_at else "",
    }


@router.put("/profile")
def update_profile(
    data: CustomerProfileIn,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if data.name:
        customer.name = data.name
    if data.email:
        customer.email = data.email
    if data.gst_number is not None:
        customer.gst_number = data.gst_number
    db.commit()
    return {"ok": True}


# ───────────────────────────── Addresses ─────────────────────────────

@router.get("/addresses")
def list_addresses(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    addrs = db.query(Address).filter(Address.customer_id == customer.id).all()
    result = []
    for a in addrs:
        out = {
            "id": a.id, "label": a.label, "name": a.name, "phone": a.phone,
            "address_line": a.address_line or "",
            "line1": a.address_line or "", "line2": a.landmark or "",
            "city": a.city, "state": a.state, "pincode": a.pincode,
            "landmark": a.landmark, "is_default": a.is_default,
        }
        result.append(out)
    return result


@router.post("/addresses", response_model=AddressOut)
def add_address(
    data: AddressIn,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    if data.is_default:
        db.query(Address).filter(Address.customer_id == customer.id).update({"is_default": False})
    addr = Address(customer_id=customer.id, **data.to_db_dict())
    db.add(addr)
    db.commit()
    db.refresh(addr)
    return addr


@router.put("/addresses/{addr_id}", response_model=AddressOut)
def update_address(
    addr_id: int,
    data: AddressIn,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    addr = db.query(Address).filter(Address.id == addr_id, Address.customer_id == customer.id).first()
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    if data.is_default:
        db.query(Address).filter(Address.customer_id == customer.id).update({"is_default": False})
    for field, val in data.to_db_dict().items():
        setattr(addr, field, val)
    db.commit()
    db.refresh(addr)
    return addr


@router.delete("/addresses/{addr_id}")
def delete_address(
    addr_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    addr = db.query(Address).filter(Address.id == addr_id, Address.customer_id == customer.id).first()
    if addr:
        db.delete(addr)
        db.commit()
    return {"ok": True}
