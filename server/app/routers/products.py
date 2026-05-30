import io
import os
import time
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..config import UPLOAD_DIR
from ..database import get_db
from ..models import AdminUser, Category, Concern, Product
from ..schemas import ProductIn, ProductOut
from ..utils import discount_pct, slugify

router = APIRouter(tags=["products"])


def to_out(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "category_id": p.category_id,
        "concerns": p.concerns or [],
        "price": p.price,
        "mrp": p.mrp,
        "rating": p.rating,
        "reviews": p.reviews,
        "emoji": p.emoji,
        "badge": p.badge or "",
        "image": p.image or "",
        "description": p.description or "",
        "benefits": p.benefits or [],
        "sizes": p.sizes or [],
        "stock": p.stock,
        "active": p.active,
        "discount_pct": discount_pct(p.price, p.mrp),
    }


# ---------------- Public ----------------
@router.get("/api/products")
def list_products(
    db: Session = Depends(get_db),
    category: str | None = Query(None),
    concern: str | None = Query(None),
    search: str | None = Query(None),
    include_inactive: bool = Query(False),
):
    q = db.query(Product)
    if not include_inactive:
        q = q.filter(Product.active == True)  # noqa: E712
    if category:
        q = q.filter(Product.category_id == category)
    items = q.all()
    out = [to_out(p) for p in items]
    if concern:
        out = [p for p in out if concern in p["concerns"]]
    if search:
        s = search.lower()
        out = [p for p in out if s in (p["name"] + " " + p["description"]).lower()]
    return out


@router.get("/api/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_out(p)


# ---------------- Admin CRUD ----------------
@router.post("/api/admin/products", response_model=ProductOut)
def create_product(
    data: ProductIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    pid = data.id or slugify(data.name)
    if db.query(Product).filter(Product.id == pid).first():
        pid = f"{pid}-{int(time.time())%10000}"
    p = Product(
        id=pid,
        name=data.name,
        category_id=data.category_id,
        concerns=data.concerns,
        price=data.price,
        mrp=data.mrp,
        rating=data.rating,
        reviews=data.reviews,
        emoji=data.emoji,
        badge=data.badge,
        image=data.image,
        description=data.description,
        benefits=data.benefits,
        sizes=data.sizes,
        stock=data.stock,
        active=data.active,
    )
    db.add(p)
    db.commit()
    return to_out(p)


@router.put("/api/admin/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: str,
    data: ProductIn,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    for field in [
        "name", "category_id", "concerns", "price", "mrp", "rating", "reviews",
        "emoji", "badge", "image", "description", "benefits", "sizes", "stock", "active",
    ]:
        setattr(p, field, getattr(data, field))
    db.commit()
    return to_out(p)


@router.delete("/api/admin/products/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# ---------------- Image upload ----------------
@router.post("/api/admin/upload")
def upload_image(
    file: UploadFile = File(...),
    admin: AdminUser = Depends(get_current_admin),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        raise HTTPException(status_code=400, detail="Unsupported image type")
    name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return {"url": f"/uploads/{name}"}


# ---------------- Excel / CSV bulk import & export ----------------
PRODUCT_COLUMNS = [
    "id", "name", "category_id", "concerns", "price", "mrp", "rating",
    "reviews", "emoji", "badge", "image", "description", "benefits", "sizes",
    "stock", "active",
]


@router.get("/api/admin/products/export.xlsx")
def export_products(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Products"
    ws.append(PRODUCT_COLUMNS)
    for p in db.query(Product).all():
        ws.append([
            p.id, p.name, p.category_id, ", ".join(p.concerns or []),
            p.price, p.mrp, p.rating, p.reviews, p.emoji, p.badge or "",
            p.image or "", p.description or "",
            " | ".join(p.benefits or []), ", ".join(p.sizes or []),
            p.stock, "yes" if p.active else "no",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=primenutra-products.xlsx"},
    )


@router.get("/api/admin/products/template.xlsx")
def template_products(admin: AdminUser = Depends(get_current_admin)):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Products"
    ws.append(PRODUCT_COLUMNS)
    ws.append([
        "tulsi-green-classic", "Tulsi Green Tea Classic", "teas",
        "immunity, metabolism", 199, 240, 4.7, 1240, "🍵", "Bestseller",
        "", "Soothing blend of holy basil and green tea.",
        "Rich in antioxidants | Supports immunity", "25 Teabags, 50 Teabags",
        100, "yes",
    ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=primenutra-products-template.xlsx"},
    )


def _split_list(val, sep):
    if val is None:
        return []
    return [x.strip() for x in str(val).replace("|", sep).split(sep) if x.strip()]


@router.post("/api/admin/products/import")
def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    fname = (file.filename or "").lower()
    raw = file.file.read()
    rows = []
    if fname.endswith(".csv"):
        import csv

        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    elif fname.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(raw))
        ws = wb.active
        header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        for r in ws.iter_rows(min_row=2, values_only=True):
            if all(v is None for v in r):
                continue
            rows.append({header[i]: r[i] for i in range(len(header)) if i < len(r)})
    else:
        raise HTTPException(status_code=400, detail="Upload a .xlsx or .csv file")

    valid_categories = {c.id for c in db.query(Category).all()}
    valid_concerns = {c.id for c in db.query(Concern).all()}
    created, updated, errors = 0, 0, []

    for i, row in enumerate(rows, start=2):
        try:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            pid = (str(row.get("id")).strip() if row.get("id") else "") or slugify(name)
            cat = (row.get("category_id") or "").strip()
            if cat and cat not in valid_categories:
                errors.append(f"Row {i}: unknown category '{cat}'")
                continue
            concerns = [c for c in _split_list(row.get("concerns"), ",") if not valid_concerns or c in valid_concerns]
            benefits = _split_list(row.get("benefits"), "|") or _split_list(row.get("benefits"), ",")
            sizes = _split_list(row.get("sizes"), ",")

            def num(v, default=0.0):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return default

            active_raw = str(row.get("active", "yes")).strip().lower()
            active = active_raw in {"yes", "true", "1", "y", ""}

            p = db.query(Product).filter(Product.id == pid).first()
            is_new = p is None
            if is_new:
                p = Product(id=pid)
                db.add(p)
            p.name = name
            p.category_id = cat or p.category_id
            if concerns:
                p.concerns = concerns
            p.price = num(row.get("price"), p.price or 0)
            p.mrp = num(row.get("mrp"), p.mrp or 0)
            p.rating = num(row.get("rating"), p.rating or 4.5)
            p.reviews = int(num(row.get("reviews"), p.reviews or 0))
            p.emoji = (row.get("emoji") or p.emoji or "🌿")
            p.badge = (row.get("badge") or "")
            p.image = (row.get("image") or p.image or "")
            p.description = (row.get("description") or p.description or "")
            if benefits:
                p.benefits = benefits
            if sizes:
                p.sizes = sizes
            p.stock = int(num(row.get("stock"), p.stock or 100))
            p.active = active
            created += 1 if is_new else 0
            updated += 0 if is_new else 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"Row {i}: {e}")

    db.commit()
    return {"created": created, "updated": updated, "errors": errors}
