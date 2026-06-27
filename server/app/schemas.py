"""PrimeNutra Wellness — Pydantic schemas (complete D2C platform)."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ───────────────────────────── Catalog ─────────────────────────────

class CategoryIn(BaseModel):
    id: str
    name: str
    emoji: str = ""
    blurb: str = ""
    image: str = ""
    sort_order: int = 0
    seo_title: str = ""
    seo_description: str = ""


class ConcernIn(BaseModel):
    id: str
    name: str
    emoji: str = ""
    blurb: str = ""
    sort_order: int = 0


class SubCategoryIn(BaseModel):
    id: str
    category_id: str
    name: str
    emoji: str = ""
    sort_order: int = 0


class BrandIn(BaseModel):
    id: str
    name: str
    logo: str = ""
    description: str = ""
    sort_order: int = 0


class ProductBase(BaseModel):
    name: str
    category_id: str
    subcategory_id: str = ""
    brand_id: str = ""
    concerns: List[str] = []
    sku: str = ""
    price: float = 0
    mrp: float = 0
    rating: float = 4.5
    reviews_count: int = 0
    emoji: str = "🌿"
    badge: str = ""
    image: str = ""
    gallery: List[str] = []
    video_url: str = ""
    description: str = ""
    specifications: Dict[str, str] = {}
    benefits: List[str] = []
    ingredients: str = ""
    faqs: list = []
    sizes: List[str] = []
    variants: list = []
    hsn_code: str = ""
    gst_rate: float = 18.0
    stock: int = 100
    low_stock_threshold: int = 5
    weight_grams: float = 0
    active: bool = True
    featured: bool = False
    seo_title: str = ""
    seo_description: str = ""


class ProductIn(ProductBase):
    id: Optional[str] = None


class ProductOut(ProductBase):
    id: str
    discount_pct: int = 0

    class Config:
        from_attributes = True


# ───────────────────────────── Auth (Admin) ─────────────────────────────

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


# ───────────────────────────── Customer Auth (OTP) ─────────────────────────────

class OTPSendIn(BaseModel):
    phone: str = Field(min_length=10, max_length=15)


class OTPVerifyIn(BaseModel):
    phone: str
    code: str


class CustomerTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_id: int
    phone: str
    name: str = ""
    is_new: bool = False


class CustomerProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    gst_number: str = ""


# ───────────────────────────── Address ─────────────────────────────

class AddressIn(BaseModel):
    label: str = "Home"
    name: str = ""
    phone: str = ""
    address_line: str = ""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    landmark: str = ""
    is_default: bool = False

    def to_db_dict(self):
        d = self.model_dump(exclude={"line1", "line2"})
        if not d["address_line"] and (self.line1 or self.line2):
            parts = [self.line1, self.line2]
            d["address_line"] = ", ".join(p for p in parts if p)
        return d


class AddressOut(BaseModel):
    id: int
    label: str = "Home"
    name: str = ""
    phone: str = ""
    address_line: str = ""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    landmark: str = ""
    is_default: bool = False

    class Config:
        from_attributes = True


# ───────────────────────────── Cart ─────────────────────────────

class CartItemIn(BaseModel):
    id: str
    size: str = ""
    qty: int = 1
    variant_index: int = -1


class CartSyncIn(BaseModel):
    items: List[CartItemIn]


# ───────────────────────────── Orders ─────────────────────────────

class CheckoutIn(BaseModel):
    customer_name: str
    phone: str
    email: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    landmark: str = ""
    gst_number: str = ""
    order_notes: str = ""
    payment_method: str = "COD"
    coupon_code: str = ""
    address_id: int = 0
    partial_amount: float = 0
    items: List[CartItemIn]


class OrderItemOut(BaseModel):
    product_id: str
    name: str
    size: str
    qty: int
    price: float
    mrp: float = 0
    sku: str = ""
    hsn_code: str = ""
    gst_rate: float = 18.0
    tax_amount: float = 0

    class Config:
        from_attributes = True


class OrderStatusLogOut(BaseModel):
    status: str
    note: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    customer_id: Optional[int] = None
    customer_name: str
    phone: str
    email: str
    address: str
    city: str
    state: str
    pincode: str
    landmark: str
    gst_number: str = ""
    order_notes: str = ""
    payment_method: str
    payment_status: str
    status: str
    subtotal: float
    discount: float
    shipping: float
    tax_amount: float = 0
    total: float
    coupon_code: str
    razorpay_order_id: str
    partial_paid: float = 0
    partial_remaining: float = 0
    courier: str = ""
    tracking_number: str = ""
    tracking_url: str = ""
    dispatch_date: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    invoice_number: str = ""
    created_at: datetime
    items: List[OrderItemOut] = []
    status_history: List[OrderStatusLogOut] = []

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str
    note: str = ""


class ShippingUpdate(BaseModel):
    courier: str = ""
    tracking_number: str = ""
    tracking_url: str = ""
    dispatch_date: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None


# ───────────────────────────── Coupons / Settings ─────────────────────────────

class CouponIn(BaseModel):
    code: str
    type: str = "percent"
    value: float = 0
    min_order: float = 0
    max_discount: float = 0
    usage_limit: int = 0
    per_user_limit: int = 0
    category_id: str = ""
    product_id: str = ""
    first_order_only: bool = False
    coupon_scope: str = "all"
    active: bool = True
    expires_at: Optional[datetime] = None


class SettingsIn(BaseModel):
    values: dict


# ───────────────────────────── Returns ─────────────────────────────

class ReturnRequestIn(BaseModel):
    order_id: str
    reason: str = ""
    images: List[str] = []


class ReturnUpdateIn(BaseModel):
    status: str
    refund_amount: float = 0
    refund_method: str = ""
    admin_notes: str = ""


# ───────────────────────────── Reviews ─────────────────────────────

class ReviewIn(BaseModel):
    product_id: str
    order_id: str = ""
    rating: int = 5
    title: str = ""
    body: str = ""
    images: List[str] = []


# ───────────────────────────── Combos ─────────────────────────────

class ComboItemIn(BaseModel):
    product_id: str
    is_trigger: bool = False


class ComboIn(BaseModel):
    name: str
    description: str = ""
    discount_type: str = "percent"
    discount_value: float = 0
    bundle_price: float = 0
    active: bool = True
    items: List[ComboItemIn] = []


# ───────────────────────────── Blog ─────────────────────────────

class BlogCategoryIn(BaseModel):
    id: str
    name: str
    sort_order: int = 0


class BlogPostIn(BaseModel):
    title: str
    slug: str = ""
    excerpt: str = ""
    body: str = ""
    cover_image: str = ""
    author: str = "PrimeNutra Wellness"
    category_id: str = ""
    tags: List[str] = []
    related_products: List[str] = []
    published: bool = False
    seo_title: str = ""
    seo_description: str = ""


# ───────────────────────────── Influencer ─────────────────────────────

class InfluencerIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    referral_code: str = ""
    coupon_code: str = ""
    commission_percent: float = 5.0
    status: str = "pending"
