"""Seed data — populate database on first run."""
import json
import os

from sqlalchemy.orm import Session

from .auth import hash_password
from .config import DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USER
from .database import SessionLocal
from .models import AdminUser, Category, Concern, Product
from .utils import ensure_default_settings

SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_data.json")


def seed_admin(db: Session):
    if db.query(AdminUser).count() == 0:
        db.add(AdminUser(
            username=DEFAULT_ADMIN_USER,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        ))
        db.commit()


def seed_catalog(db: Session):
    """Populate categories, concerns and products on an empty catalog only."""
    if db.query(Product).count() > 0:
        return
    if not os.path.exists(SEED_FILE):
        return
    with open(SEED_FILE, encoding="utf-8") as f:
        data = json.load(f)

    for i, c in enumerate(data.get("CATEGORIES", [])):
        if not db.query(Category).filter(Category.id == c["id"]).first():
            db.add(Category(id=c["id"], name=c["name"], emoji=c.get("emoji", ""),
                            blurb=c.get("blurb", ""), sort_order=i))
    for i, c in enumerate(data.get("CONCERNS", [])):
        if not db.query(Concern).filter(Concern.id == c["id"]).first():
            db.add(Concern(id=c["id"], name=c["name"], emoji=c.get("emoji", ""),
                           blurb=c.get("blurb", ""), sort_order=i))
    db.commit()

    for p in data.get("PRODUCTS", []):
        if db.query(Product).filter(Product.id == p["id"]).first():
            continue
        db.add(Product(
            id=p["id"],
            name=p["name"],
            category_id=p.get("category"),
            concerns=p.get("concerns", []),
            price=p.get("price", 0),
            mrp=p.get("mrp", 0),
            rating=p.get("rating", 4.5),
            reviews_count=p.get("reviews", 0),
            emoji=p.get("emoji", "🌿"),
            badge=p.get("badge", ""),
            description=p.get("desc", ""),
            benefits=p.get("benefits", []),
            sizes=p.get("sizes", []),
            stock=100,
            active=True,
        ))
    db.commit()


def run_seed():
    """Run seed using own db session."""
    db = SessionLocal()
    try:
        ensure_default_settings(db)
        seed_admin(db)
        seed_catalog(db)
    finally:
        db.close()
