"""Admin — login, settings, customers, notifications, SEO, inventory, reviews."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from ..database import get_db
from ..models import (
    AdminUser, AuditLog, BlogPost, Category, ComboItem, ComboProduct,
    Concern, Coupon, Customer, InventoryLog, Notification, Product,
    Redirect, Review, Setting,
)
from ..schemas import (
    CategoryIn, ConcernIn, CouponIn, LoginIn, PasswordChange,
    SettingsIn, TokenOut,
)
from ..utils import get_settings, set_setting

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ───────────────────────────── Auth ─────────────────────────────

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Bad credentials")
    token = create_access_token(user.username)
    return TokenOut(access_token=token, username=user.username)


@router.get("/me")
def admin_me(admin: AdminUser = Depends(get_current_admin)):
    return {"username": admin.username, "role": admin.role}


@router.post("/change-password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Wrong current password")
    admin.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}


# ───────────────────────────── Settings ─────────────────────────────

@router.get("/settings")
def read_settings(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return get_settings(db)


@router.put("/settings")
def update_settings(data: SettingsIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    for key, value in data.values.items():
        set_setting(db, key, str(value))
    db.commit()
    return {"ok": True}


# ───────────────────────────── Categories ─────────────────────────────

@router.get("/categories")
def list_cats(db: Session = Depends(get_db)):
    return [
        {
            "id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb,
            "image": c.image or "", "sort_order": c.sort_order,
            "seo_title": c.seo_title or "", "seo_description": c.seo_description or "",
        }
        for c in db.query(Category).order_by(Category.sort_order).all()
    ]


@router.post("/categories")
def upsert_cat(data: CategoryIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(Category).filter(Category.id == data.id).first()
    if not c:
        c = Category(id=data.id)
        db.add(c)
    c.name = data.name
    c.emoji = data.emoji
    c.blurb = data.blurb
    c.image = data.image
    c.sort_order = data.sort_order
    c.seo_title = data.seo_title
    c.seo_description = data.seo_description
    db.commit()
    return {"ok": True}


@router.delete("/categories/{cid}")
def delete_cat(cid: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(Category).filter(Category.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}


# ───────────────────────────── Concerns ─────────────────────────────

@router.get("/concerns")
def list_conc(db: Session = Depends(get_db)):
    return [
        {"id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb}
        for c in db.query(Concern).order_by(Concern.sort_order).all()
    ]


@router.post("/concerns")
def upsert_conc(data: ConcernIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(Concern).filter(Concern.id == data.id).first()
    if not c:
        c = Concern(id=data.id)
        db.add(c)
    c.name = data.name
    c.emoji = data.emoji
    c.blurb = data.blurb
    c.sort_order = data.sort_order
    db.commit()
    return {"ok": True}


@router.delete("/concerns/{cid}")
def delete_conc(cid: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(Concern).filter(Concern.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}


# ───────────────────────────── Coupons ─────────────────────────────

@router.get("/coupons")
def list_coupons(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return [
        {
            "id": c.id, "code": c.code, "type": c.type, "value": c.value,
            "min_order": c.min_order, "max_discount": c.max_discount,
            "usage_limit": c.usage_limit, "per_user_limit": c.per_user_limit,
            "used_count": c.used_count, "active": c.active,
            "first_order_only": c.first_order_only,
            "category_id": c.category_id, "product_id": c.product_id,
            "coupon_scope": c.coupon_scope,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        }
        for c in db.query(Coupon).order_by(Coupon.id.desc()).all()
    ]


@router.post("/coupons")
def upsert_coupon(data: CouponIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    code = data.code.strip().upper()
    c = db.query(Coupon).filter(Coupon.code == code).first()
    if not c:
        c = Coupon(code=code)
        db.add(c)
    c.type = data.type
    c.value = data.value
    c.min_order = data.min_order
    c.max_discount = data.max_discount
    c.usage_limit = data.usage_limit
    c.per_user_limit = data.per_user_limit
    c.first_order_only = data.first_order_only
    c.category_id = data.category_id
    c.product_id = data.product_id
    c.coupon_scope = data.coupon_scope
    c.active = data.active
    c.expires_at = data.expires_at
    db.commit()
    return {"ok": True, "id": c.id}


@router.delete("/coupons/{code}")
def delete_coupon(code: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    c = db.query(Coupon).filter(Coupon.code == code.upper()).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}


# ───────────────────────────── Customers ─────────────────────────────

@router.get("/customers")
def list_customers(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).all()
    return [
        {
            "id": c.id, "phone": c.phone, "name": c.name, "email": c.email,
            "gst_number": c.gst_number, "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in customers
    ]


# ───────────────────────────── Notifications ─────────────────────────────

@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    notifs = db.query(Notification).order_by(Notification.created_at.desc()).limit(200).all()
    return [
        {
            "id": n.id, "channel": n.channel, "recipient": n.recipient,
            "event_type": n.event_type, "subject": n.subject,
            "status": n.status, "error": n.error,
            "created_at": n.created_at.isoformat() if n.created_at else "",
        }
        for n in notifs
    ]


# ───────────────────────────── Inventory Logs ─────────────────────────────

@router.get("/inventory-logs")
def list_inventory_logs(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    logs = db.query(InventoryLog).order_by(InventoryLog.created_at.desc()).limit(200).all()
    return [
        {
            "id": l.id, "product_id": l.product_id, "change": l.change,
            "reason": l.reason, "note": l.note,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in logs
    ]


# ───────────────────────────── SEO Redirects ─────────────────────────────

@router.get("/redirects")
def list_redirects(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return [
        {"id": r.id, "from_path": r.from_path, "to_path": r.to_path, "type": r.type}
        for r in db.query(Redirect).all()
    ]


@router.post("/redirects")
def add_redirect(from_path: str, to_path: str, rtype: int = 301,
                 db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    r = Redirect(from_path=from_path, to_path=to_path, type=rtype)
    db.add(r)
    db.commit()
    return {"ok": True, "id": r.id}


@router.delete("/redirects/{rid}")
def delete_redirect(rid: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    r = db.query(Redirect).filter(Redirect.id == rid).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


# ───────────────────────────── Audit Log ─────────────────────────────

@router.get("/audit-logs")
def list_audit_logs(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [
        {
            "id": l.id, "admin_username": l.admin_username, "action": l.action,
            "resource": l.resource, "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        }
        for l in logs
    ]


# ───────────────────────────── Reviews ─────────────────────────────

@router.get("/reviews")
def list_reviews(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    reviews = db.query(Review).order_by(Review.created_at.desc()).limit(200).all()
    return [
        {
            "id": r.id, "product_id": r.product_id, "customer_id": r.customer_id,
            "rating": r.rating, "title": r.title, "body": r.body,
            "verified_purchase": r.verified_purchase, "approved": r.approved,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in reviews
    ]


@router.put("/reviews/{review_id}/approve")
def approve_review(review_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Review not found")
    r.approved = True
    db.commit()
    # Update product rating
    product = db.query(Product).filter(Product.id == r.product_id).first()
    if product:
        approved_reviews = db.query(Review).filter(Review.product_id == r.product_id, Review.approved == True).all()
        if approved_reviews:
            product.rating = round(sum(rv.rating for rv in approved_reviews) / len(approved_reviews), 1)
            product.reviews_count = len(approved_reviews)
            db.commit()
    return {"ok": True}


@router.delete("/reviews/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}


# ───────────────────────────── Combos (admin) ─────────────────────────────

@router.get("/combos")
def list_combos_admin(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    combos = db.query(ComboProduct).order_by(ComboProduct.id.desc()).all()
    result = []
    for c in combos:
        items = []
        for it in c.items:
            prod = db.query(Product).filter(Product.id == it.product_id).first()
            items.append({
                "product_id": it.product_id,
                "product_name": prod.name if prod else it.product_id,
                "is_trigger": it.is_trigger,
            })
        result.append({
            "id": c.id, "name": c.name, "description": c.description,
            "discount_type": c.discount_type, "discount_value": c.discount_value,
            "bundle_price": c.bundle_price, "active": c.active,
            "items": items,
        })
    return result


# ───────────────────────────── Blog (admin) ─────────────────────────────

@router.get("/blog/posts")
def list_blog_posts_admin(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    posts = db.query(BlogPost).order_by(BlogPost.created_at.desc()).all()
    return [
        {
            "id": p.id, "slug": p.slug, "title": p.title, "author": p.author,
            "published": p.published, "views": p.views,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        for p in posts
    ]
