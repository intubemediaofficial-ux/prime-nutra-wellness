from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, Category, Concern, Product
from ..schemas import CategoryIn, ConcernIn
from ..utils import slugify

router = APIRouter(tags=["categories"])


@router.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    return [
        {"id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb}
        for c in db.query(Category).order_by(Category.sort_order).all()
    ]


@router.get("/api/concerns")
def list_concerns(db: Session = Depends(get_db)):
    return [
        {"id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb}
        for c in db.query(Concern).order_by(Concern.sort_order).all()
    ]


# ---------- Admin: categories ----------
@router.post("/api/admin/categories")
def upsert_category(
    data: CategoryIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    cid = data.id or slugify(data.name)
    c = db.query(Category).filter(Category.id == cid).first()
    if not c:
        c = Category(id=cid)
        db.add(c)
    c.name, c.emoji, c.blurb, c.sort_order = data.name, data.emoji, data.blurb, data.sort_order
    db.commit()
    return {"id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb}


@router.delete("/api/admin/categories/{cid}")
def delete_category(
    cid: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if db.query(Product).filter(Product.category_id == cid).count():
        raise HTTPException(status_code=400, detail="Category has products; reassign them first")
    c = db.query(Category).filter(Category.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}


# ---------- Admin: concerns ----------
@router.post("/api/admin/concerns")
def upsert_concern(
    data: ConcernIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    cid = data.id or slugify(data.name)
    c = db.query(Concern).filter(Concern.id == cid).first()
    if not c:
        c = Concern(id=cid)
        db.add(c)
    c.name, c.emoji, c.blurb, c.sort_order = data.name, data.emoji, data.blurb, data.sort_order
    db.commit()
    return {"id": c.id, "name": c.name, "emoji": c.emoji, "blurb": c.blurb}


@router.delete("/api/admin/concerns/{cid}")
def delete_concern(
    cid: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    c = db.query(Concern).filter(Concern.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}
