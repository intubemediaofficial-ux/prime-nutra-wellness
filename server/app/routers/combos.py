"""Combo products — create/manage bundles, suggest combos on product/cart."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, ComboItem, ComboProduct, Product
from ..schemas import ComboIn

router = APIRouter(tags=["combos"])


def _combo_out(combo: ComboProduct):
    return {
        "id": combo.id,
        "name": combo.name,
        "description": combo.description,
        "discount_type": combo.discount_type,
        "discount_value": combo.discount_value,
        "bundle_price": combo.bundle_price,
        "active": combo.active,
        "items": [
            {
                "product_id": ci.product_id,
                "is_trigger": ci.is_trigger,
                "product_name": ci.product.name if ci.product else "",
                "product_price": ci.product.price if ci.product else 0,
                "product_image": ci.product.image if ci.product else "",
            }
            for ci in combo.items
        ],
    }


@router.get("/api/combos")
def list_combos(db: Session = Depends(get_db)):
    combos = db.query(ComboProduct).filter(ComboProduct.active == True).all()
    return [_combo_out(c) for c in combos]


@router.get("/api/combos/for-product/{product_id}")
def combos_for_product(product_id: str, db: Session = Depends(get_db)):
    """Get combo suggestions when viewing a product."""
    trigger_items = (
        db.query(ComboItem)
        .filter(ComboItem.product_id == product_id, ComboItem.is_trigger == True)
        .all()
    )
    combo_ids = {ci.combo_id for ci in trigger_items}
    if not combo_ids:
        return []
    combos = (
        db.query(ComboProduct)
        .filter(ComboProduct.id.in_(combo_ids), ComboProduct.active == True)
        .all()
    )
    return [_combo_out(c) for c in combos]


@router.get("/api/combos/for-cart")
def combos_for_cart(product_ids: str = "", db: Session = Depends(get_db)):
    """Suggest combos based on products in cart (comma-separated IDs)."""
    if not product_ids:
        return []
    pids = [p.strip() for p in product_ids.split(",") if p.strip()]
    trigger_items = (
        db.query(ComboItem)
        .filter(ComboItem.product_id.in_(pids), ComboItem.is_trigger == True)
        .all()
    )
    combo_ids = {ci.combo_id for ci in trigger_items}
    if not combo_ids:
        return []
    combos = (
        db.query(ComboProduct)
        .filter(ComboProduct.id.in_(combo_ids), ComboProduct.active == True)
        .all()
    )
    return [_combo_out(c) for c in combos]


# ───────────────────────────── Admin ─────────────────────────────

@router.get("/api/admin/combos")
def admin_list_combos(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    return [_combo_out(c) for c in db.query(ComboProduct).all()]


@router.post("/api/admin/combos")
def create_combo(data: ComboIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    combo = ComboProduct(
        name=data.name,
        description=data.description,
        discount_type=data.discount_type,
        discount_value=data.discount_value,
        bundle_price=data.bundle_price,
        active=data.active,
    )
    db.add(combo)
    db.flush()
    for item in data.items:
        db.add(ComboItem(combo_id=combo.id, product_id=item.product_id, is_trigger=item.is_trigger))
    db.commit()
    db.refresh(combo)
    return _combo_out(combo)


@router.put("/api/admin/combos/{combo_id}")
def update_combo(combo_id: int, data: ComboIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    combo = db.query(ComboProduct).filter(ComboProduct.id == combo_id).first()
    if not combo:
        raise HTTPException(status_code=404, detail="Combo not found")
    combo.name = data.name
    combo.description = data.description
    combo.discount_type = data.discount_type
    combo.discount_value = data.discount_value
    combo.bundle_price = data.bundle_price
    combo.active = data.active
    db.query(ComboItem).filter(ComboItem.combo_id == combo_id).delete()
    for item in data.items:
        db.add(ComboItem(combo_id=combo_id, product_id=item.product_id, is_trigger=item.is_trigger))
    db.commit()
    return _combo_out(combo)


@router.delete("/api/admin/combos/{combo_id}")
def delete_combo(combo_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    combo = db.query(ComboProduct).filter(ComboProduct.id == combo_id).first()
    if combo:
        db.delete(combo)
        db.commit()
    return {"ok": True}
