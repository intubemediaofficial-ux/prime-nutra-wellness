from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ---------- Catalog ----------
class CategoryIn(BaseModel):
    id: str
    name: str
    emoji: str = ""
    blurb: str = ""
    sort_order: int = 0


class ConcernIn(CategoryIn):
    pass


class ProductBase(BaseModel):
    name: str
    category_id: str
    concerns: List[str] = []
    price: float = 0
    mrp: float = 0
    rating: float = 4.5
    reviews: int = 0
    emoji: str = "🌿"
    badge: str = ""
    image: str = ""
    description: str = ""
    benefits: List[str] = []
    sizes: List[str] = []
    stock: int = 100
    active: bool = True


class ProductIn(ProductBase):
    id: Optional[str] = None  # auto-slug from name if omitted


class ProductOut(ProductBase):
    id: str
    discount_pct: int = 0

    class Config:
        from_attributes = True


# ---------- Auth ----------
class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


# ---------- Orders ----------
class CartItemIn(BaseModel):
    id: str
    size: str = ""
    qty: int = 1


class CheckoutIn(BaseModel):
    customer_name: str
    phone: str
    email: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    landmark: str = ""
    payment_method: str = "COD"
    coupon_code: str = ""
    items: List[CartItemIn]


class OrderItemOut(BaseModel):
    product_id: str
    name: str
    size: str
    qty: int
    price: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    customer_name: str
    phone: str
    email: str
    address: str
    city: str
    state: str
    pincode: str
    landmark: str
    payment_method: str
    payment_status: str
    status: str
    subtotal: float
    discount: float
    shipping: float
    total: float
    coupon_code: str
    razorpay_order_id: str
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


# ---------- Coupons / Settings ----------
class CouponIn(BaseModel):
    code: str
    type: str = "percent"
    value: float = 0
    min_order: float = 0
    active: bool = True
    expires_at: Optional[datetime] = None


class SettingsIn(BaseModel):
    # arbitrary key/value pairs
    values: dict
