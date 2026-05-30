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


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # admin | staff
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"
    id = Column(String(40), primary_key=True)  # slug
    name = Column(String(120), nullable=False)
    emoji = Column(String(16), default="")
    blurb = Column(String(255), default="")
    sort_order = Column(Integer, default=0)


class Concern(Base):
    __tablename__ = "concerns"
    id = Column(String(40), primary_key=True)  # slug
    name = Column(String(120), nullable=False)
    emoji = Column(String(16), default="")
    blurb = Column(String(255), default="")
    sort_order = Column(Integer, default=0)


class Product(Base):
    __tablename__ = "products"
    id = Column(String(80), primary_key=True)  # slug
    name = Column(String(200), nullable=False)
    category_id = Column(String(40), ForeignKey("categories.id"))
    concerns = Column(JSON, default=list)       # list[str] of concern ids
    price = Column(Float, nullable=False, default=0)
    mrp = Column(Float, nullable=False, default=0)
    rating = Column(Float, default=4.5)
    reviews = Column(Integer, default=0)
    emoji = Column(String(16), default="🌿")
    badge = Column(String(40), default="")
    image = Column(String(255), default="")     # uploaded image path (relative URL)
    description = Column(Text, default="")
    benefits = Column(JSON, default=list)        # list[str]
    sizes = Column(JSON, default=list)           # list[str]
    stock = Column(Integer, default=100)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String(24), primary_key=True)  # PNWxxxxxxxx
    customer_name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(120), default="")
    address = Column(Text, default="")
    city = Column(String(80), default="")
    state = Column(String(80), default="")
    pincode = Column(String(12), default="")
    landmark = Column(String(120), default="")
    payment_method = Column(String(20), default="COD")   # COD | Razorpay
    payment_status = Column(String(20), default="pending")  # pending | paid | failed
    status = Column(String(20), default="placed")  # placed|confirmed|shipped|delivered|cancelled
    subtotal = Column(Float, default=0)
    discount = Column(Float, default=0)
    shipping = Column(Float, default=0)
    total = Column(Float, default=0)
    coupon_code = Column(String(40), default="")
    razorpay_order_id = Column(String(80), default="")
    razorpay_payment_id = Column(String(80), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(String(24), ForeignKey("orders.id"))
    product_id = Column(String(80))
    name = Column(String(200))
    size = Column(String(80), default="")
    qty = Column(Integer, default=1)
    price = Column(Float, default=0)

    order = relationship("Order", back_populates="items")


class Coupon(Base):
    __tablename__ = "coupons"
    code = Column(String(40), primary_key=True)
    type = Column(String(10), default="percent")  # percent | flat
    value = Column(Float, default=0)
    min_order = Column(Float, default=0)
    active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(60), primary_key=True)
    value = Column(Text, default="")
