"""Shared utilities for PrimeNutra Wellness backend."""
import re

from sqlalchemy.orm import Session

from .models import Setting

DEFAULT_SETTINGS = {
    "store_name": "PrimeNutra Wellness",
    "whatsapp_number": "919999999999",
    "cod_enabled": "true",
    "cod_min_order": "0",
    "cod_max_order": "0",
    "cod_charge": "0",
    "razorpay_enabled": "false",
    "razorpay_key_id": "",
    "razorpay_key_secret": "",
    "partial_payment_enabled": "false",
    "partial_min_advance": "500",
    "free_ship_threshold": "0",
    "shipping_fee": "0",
    "support_email": "care@primenutrawellness.in",
    "support_phone": "",
    "brevo_from_email": "care@primenutrawellness.in",
    "brevo_from_name": "PrimeNutra Wellness",
    "brevo_api_key": "",
    "whatsapp_api_key": "",
    "whatsapp_api_url": "",
    "gst_number": "",
    "company_name": "PrimeNutra Wellness",
    "company_address": "",
    "company_state": "",
    "company_state_code": "",
    "invoice_prefix": "INV",
    "invoice_counter": "0",
    "ga4_measurement_id": "",
    "gtm_container_id": "",
    "meta_pixel_id": "",
    "fb_access_token": "",
    "otp_provider": "console",  # console | twilio | msg91
    "otp_api_key": "",
    "otp_sender_id": "",
}

SECRET_SETTING_KEYS = {"razorpay_key_secret", "brevo_api_key", "whatsapp_api_key",
                       "fb_access_token", "otp_api_key"}


def slugify(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "item"


def discount_pct(price: float, mrp: float) -> int:
    if not mrp or mrp <= 0 or price >= mrp:
        return 0
    return round((mrp - price) / mrp * 100)


def get_settings(db: Session) -> dict:
    rows = {s.key: s.value for s in db.query(Setting).all()}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(rows)
    return merged


def get_public_settings(db: Session) -> dict:
    s = get_settings(db)
    return {k: v for k, v in s.items() if k not in SECRET_SETTING_KEYS}


def set_setting(db: Session, key: str, value: str):
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def ensure_default_settings(db: Session):
    existing = {s.key for s in db.query(Setting).all()}
    for k, v in DEFAULT_SETTINGS.items():
        if k not in existing:
            db.add(Setting(key=k, value=v))
    db.commit()
