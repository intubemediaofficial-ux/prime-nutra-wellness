"""PrimeNutra Wellness — SQLAlchemy ORM models (complete D2C platform)."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


# ───────────────────────────── Admin ─────────────────────────────

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=datetime.utcnow)


# ───────────────────────────── Customer ─────────────────────────────

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(120), default="")
    email = Column(String(120), default="")
    gst_number = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    addresses = relationship("Address", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer")
    wishlist_items = relationship("WishlistItem", back_populates="customer", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="customer", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="customer")
    recently_viewed = relationship("RecentlyViewed", back_populates="customer", cascade="all, delete-orphan")


class OTP(Base):
    __tablename__ = "otps"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), default="login")
    verified = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    label = Column(String(40), default="Home")
    name = Column(String(120), default="")
    phone = Column(String(20), default="")
    address_line = Column(Text, default="")
    city = Column(String(80), default="")
    state = Column(String(80), default="")
    pincode = Column(String(12), default="")
    landmark = Column(String(120), default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="addresses")


# ───────────────────────────── Catalog ─────────────────────────────

class Category(Base):
    __tablename__ = "categories"
    id = Column(String(40), primary_key=True)
    name = Column(String(120), nullable=False)
    emoji = Column(String(16), default="")
    blurb = Column(String(255), default="")
    image = Column(String(255), default="")
    sort_order = Column(Integer, default=0)
    seo_title = Column(String(200), default="")
    seo_description = Column(Text, default="")

    subcategories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")


class SubCategory(Base):
    __tablename__ = "subcategories"
    id = Column(String(40), primary_key=True)
    category_id = Column(String(40), ForeignKey("categories.id"), nullable=False)
    name = Column(String(120), nullable=False)
    emoji = Column(String(16), default="")
    sort_order = Column(Integer, default=0)

    category = relationship("Category", back_populates="subcategories")


class Brand(Base):
    __tablename__ = "brands"
    id = Column(String(40), primary_key=True)
    name = Column(String(120), nullable=False)
    logo = Column(String(255), default="")
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)


class Concern(Base):
    __tablename__ = "concerns"
    id = Column(String(40), primary_key=True)
    name = Column(String(120), nullable=False)
    emoji = Column(String(16), default="")
    blurb = Column(String(255), default="")
    sort_order = Column(Integer, default=0)


class Product(Base):
    __tablename__ = "products"
    id = Column(String(80), primary_key=True)
    name = Column(String(200), nullable=False)
    category_id = Column(String(40), ForeignKey("categories.id"))
    subcategory_id = Column(String(40), ForeignKey("subcategories.id"), nullable=True)
    brand_id = Column(String(40), ForeignKey("brands.id"), nullable=True)
    concerns = Column(JSON, default=list)
    sku = Column(String(60), default="")
    price = Column(Float, nullable=False, default=0)
    mrp = Column(Float, nullable=False, default=0)
    rating = Column(Float, default=4.5)
    reviews_count = Column(Integer, default=0)
    emoji = Column(String(16), default="🌿")
    badge = Column(String(40), default="")
    image = Column(String(255), default="")
    gallery = Column(JSON, default=list)       # list of image URLs
    video_url = Column(String(255), default="")
    description = Column(Text, default="")
    specifications = Column(JSON, default=dict)  # key-value pairs
    benefits = Column(JSON, default=list)
    ingredients = Column(Text, default="")
    faqs = Column(JSON, default=list)           # [{q, a}]
    sizes = Column(JSON, default=list)
    variants = Column(JSON, default=list)       # [{name, price, mrp, sku, stock}]
    hsn_code = Column(String(20), default="")
    gst_rate = Column(Float, default=18.0)
    stock = Column(Integer, default=100)
    low_stock_threshold = Column(Integer, default=5)
    weight_grams = Column(Float, default=0)
    active = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    seo_title = Column(String(200), default="")
    seo_description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category")
    subcategory = relationship("SubCategory")
    brand = relationship("Brand")
    review_list = relationship("Review", back_populates="product")


# ───────────────────────────── Combos ─────────────────────────────

class ComboProduct(Base):
    __tablename__ = "combo_products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    discount_type = Column(String(10), default="percent")  # percent | flat | free
    discount_value = Column(Float, default=0)
    bundle_price = Column(Float, default=0)       # if set, overrides discount calc
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("ComboItem", back_populates="combo", cascade="all, delete-orphan")


class ComboItem(Base):
    __tablename__ = "combo_items"
    id = Column(Integer, primary_key=True)
    combo_id = Column(Integer, ForeignKey("combo_products.id"), nullable=False)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    is_trigger = Column(Boolean, default=False)   # product that triggers combo suggestion

    combo = relationship("ComboProduct", back_populates="items")
    product = relationship("Product")


# ───────────────────────────── Wishlist & Cart ─────────────────────────────

class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="wishlist_items")
    product = relationship("Product")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    size = Column(String(80), default="")
    variant_index = Column(Integer, default=-1)
    qty = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="cart_items")
    product = relationship("Product")


class RecentlyViewed(Base):
    __tablename__ = "recently_viewed"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="recently_viewed")
    product = relationship("Product")


# ───────────────────────────── Reviews ─────────────────────────────

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(String(24), default="")
    rating = Column(Integer, default=5)
    title = Column(String(200), default="")
    body = Column(Text, default="")
    images = Column(JSON, default=list)
    verified_purchase = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="review_list")
    customer = relationship("Customer", back_populates="reviews")


# ───────────────────────────── Orders ─────────────────────────────

class Order(Base):
    __tablename__ = "orders"
    id = Column(String(24), primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(120), default="")
    address = Column(Text, default="")
    city = Column(String(80), default="")
    state = Column(String(80), default="")
    pincode = Column(String(12), default="")
    landmark = Column(String(120), default="")
    gst_number = Column(String(20), default="")
    order_notes = Column(Text, default="")
    payment_method = Column(String(20), default="COD")
    payment_status = Column(String(20), default="pending")
    status = Column(String(20), default="placed")
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    shipping = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    cgst = Column(Float, default=0)
    sgst = Column(Float, default=0)
    igst = Column(Float, default=0)
    total = Column(Float, default=0)
    coupon_code = Column(String(40), default="")
    razorpay_order_id = Column(String(80), default="")
    razorpay_payment_id = Column(String(80), default="")
    partial_paid = Column(Float, default=0)
    partial_remaining = Column(Float, default=0)
    # shipping
    courier = Column(String(60), default="")
    tracking_number = Column(String(80), default="")
    tracking_url = Column(String(255), default="")
    dispatch_date = Column(DateTime, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    # invoice
    invoice_number = Column(String(40), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusLog", back_populates="order", cascade="all, delete-orphan")
    return_requests = relationship("ReturnRequest", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(24), ForeignKey("orders.id"))
    product_id = Column(String(80))
    name = Column(String(200))
    size = Column(String(80), default="")
    sku = Column(String(60), default="")
    hsn_code = Column(String(20), default="")
    qty = Column(Integer, default=1)
    price = Column(Float, default=0)
    mrp = Column(Float, default=0)
    gst_rate = Column(Float, default=18.0)
    tax_amount = Column(Float, default=0)

    order = relationship("Order", back_populates="items")


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(24), ForeignKey("orders.id"), nullable=False)
    status = Column(String(20), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="status_history")


# ───────────────────────────── Return & Refund ─────────────────────────────

class ReturnRequest(Base):
    __tablename__ = "return_requests"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(24), ForeignKey("orders.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    reason = Column(Text, default="")
    images = Column(JSON, default=list)
    status = Column(String(20), default="requested")  # requested|approved|rejected|refunded|partial_refunded
    refund_amount = Column(Float, default=0)
    refund_method = Column(String(20), default="")  # original|bank|wallet
    admin_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="return_requests")
    customer = relationship("Customer")


# ───────────────────────────── Coupons ─────────────────────────────

class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(40), unique=True, nullable=False)
    type = Column(String(10), default="percent")  # percent | flat | free_shipping
    value = Column(Float, default=0)
    min_order = Column(Float, default=0)
    max_discount = Column(Float, default=0)
    usage_limit = Column(Integer, default=0)       # 0 = unlimited
    per_user_limit = Column(Integer, default=0)    # 0 = unlimited
    used_count = Column(Integer, default=0)
    category_id = Column(String(40), default="")   # restrict to category
    product_id = Column(String(80), default="")    # restrict to product
    first_order_only = Column(Boolean, default=False)
    coupon_scope = Column(String(20), default="all")  # all|category|product|influencer|referral
    active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CouponUsage(Base):
    __tablename__ = "coupon_usage"
    id = Column(Integer, primary_key=True)
    coupon_code = Column(String(40), ForeignKey("coupons.code"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    order_id = Column(String(24), default="")
    used_at = Column(DateTime, default=datetime.utcnow)


# ───────────────────────────── Influencer & Referral ─────────────────────────────

class Influencer(Base):
    __tablename__ = "influencers"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), default="")
    phone = Column(String(20), default="")
    referral_code = Column(String(40), unique=True, nullable=False)
    referral_url = Column(String(255), default="")
    coupon_code = Column(String(40), default="")
    commission_percent = Column(Float, default=5.0)
    status = Column(String(20), default="pending")  # pending|approved|rejected|suspended
    total_clicks = Column(Integer, default=0)
    total_orders = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)
    total_commission = Column(Float, default=0)
    paid_commission = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReferralVisit(Base):
    __tablename__ = "referral_visits"
    id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False)
    ip_address = Column(String(45), default="")
    user_agent = Column(String(255), default="")
    visited_at = Column(DateTime, default=datetime.utcnow)


class ReferralOrder(Base):
    __tablename__ = "referral_orders"
    id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False)
    order_id = Column(String(24), ForeignKey("orders.id"), nullable=False)
    commission = Column(Float, default=0)
    paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ───────────────────────────── Blog ─────────────────────────────

class BlogCategory(Base):
    __tablename__ = "blog_categories"
    id = Column(String(40), primary_key=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, default=0)


class BlogPost(Base):
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    excerpt = Column(Text, default="")
    body = Column(Text, default="")
    cover_image = Column(String(255), default="")
    author = Column(String(120), default="PrimeNutra Wellness")
    category_id = Column(String(40), ForeignKey("blog_categories.id"), nullable=True)
    tags = Column(JSON, default=list)
    related_products = Column(JSON, default=list)  # list of product IDs
    published = Column(Boolean, default=False)
    seo_title = Column(String(200), default="")
    seo_description = Column(Text, default="")
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("BlogCategory")


# ───────────────────────────── Inventory ─────────────────────────────

class InventoryLog(Base):
    __tablename__ = "inventory_logs"
    id = Column(Integer, primary_key=True)
    product_id = Column(String(80), ForeignKey("products.id"), nullable=False)
    change = Column(Integer, default=0)  # positive = added, negative = deducted
    reason = Column(String(80), default="")  # sale|return|adjustment|restock
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ───────────────────────────── Notifications ─────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(40), default="")  # order_placed|payment|dispatch|delivered|refund|otp
    channel = Column(String(20), default="email")  # email|whatsapp|sms
    recipient = Column(String(120), default="")
    subject = Column(String(200), default="")
    body = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending|sent|failed
    error = Column(Text, default="")
    reference_id = Column(String(40), default="")  # order_id etc.
    created_at = Column(DateTime, default=datetime.utcnow)


# ───────────────────────────── Settings (existing) ─────────────────────────────

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(60), primary_key=True)
    value = Column(Text, default="")


# ───────────────────────────── SEO Redirects ─────────────────────────────

class Redirect(Base):
    __tablename__ = "redirects"
    id = Column(Integer, primary_key=True)
    from_path = Column(String(255), unique=True, nullable=False)
    to_path = Column(String(255), nullable=False)
    type = Column(Integer, default=301)
    active = Column(Boolean, default=True)


# ───────────────────────────── Audit Log ─────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    admin_username = Column(String(80), default="")
    action = Column(String(60), default="")
    resource = Column(String(120), default="")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
