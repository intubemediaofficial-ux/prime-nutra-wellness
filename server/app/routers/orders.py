import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, Coupon, Order, OrderItem, Product
from ..schemas import CheckoutIn, OrderOut, StatusUpdate
from ..utils import get_settings
from ..emailer import send_order_email

router = APIRouter(tags=["orders"])

ORDER_STATUSES = ["placed", "confirmed", "shipped", "delivered", "cancelled"]


def compute_order(db: Session, data: CheckoutIn):
    """Return (subtotal, discount, shipping, total, line_items) computed server-side."""
    settings = get_settings(db)
    line_items = []
    subtotal = 0.0
    for ci in data.items:
        p = db.query(Product).filter(Product.id == ci.id, Product.active == True).first()  # noqa: E712
        if not p:
            raise HTTPException(status_code=400, detail=f"Product unavailable: {ci.id}")
        qty = max(1, int(ci.qty))
        line_total = p.price * qty
        subtotal += line_total
        line_items.append({"product": p, "size": ci.size, "qty": qty, "price": p.price})

    # automatic discount tiers
    discount = 0.0
    if subtotal >= 1599:
        discount = round(subtotal * 0.12)
    elif subtotal >= 1299:
        discount = round(subtotal * 0.10)
    elif subtotal >= 999:
        discount = round(subtotal * 0.08)

    # coupon (overrides tier if larger)
    code = (data.coupon_code or "").strip().upper()
    if code:
        c = db.query(Coupon).filter(Coupon.code == code, Coupon.active == True).first()  # noqa: E712
        if c and subtotal >= (c.min_order or 0) and (not c.expires_at or c.expires_at >= datetime.utcnow()):
            cdisc = subtotal * (c.value / 100) if c.type == "percent" else c.value
            discount = max(discount, round(min(cdisc, subtotal)))

    threshold = float(settings.get("free_ship_threshold", "0") or 0)
    fee = float(settings.get("shipping_fee", "0") or 0)
    shipping = 0.0 if (threshold and subtotal >= threshold) or fee == 0 else fee

    total = max(0, subtotal - discount + shipping)
    return subtotal, discount, shipping, total, line_items


@router.post("/api/checkout/quote")
def quote(data: CheckoutIn, db: Session = Depends(get_db)):
    subtotal, discount, shipping, total, _ = compute_order(db, data)
    return {"subtotal": subtotal, "discount": discount, "shipping": shipping, "total": total}


@router.post("/api/orders", response_model=OrderOut)
def place_order(data: CheckoutIn, db: Session = Depends(get_db)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    settings = get_settings(db)
    method = data.payment_method if data.payment_method in {"COD", "Razorpay"} else "COD"
    if method == "COD" and settings.get("cod_enabled", "true") != "true":
        raise HTTPException(status_code=400, detail="COD is currently disabled")

    subtotal, discount, shipping, total, line_items = compute_order(db, data)
    oid = "PNW" + str(int(time.time() * 1000))[-9:]
    order = Order(
        id=oid,
        customer_name=data.customer_name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        landmark=data.landmark,
        payment_method=method,
        payment_status="pending",
        status="placed",
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        total=total,
        coupon_code=(data.coupon_code or "").strip().upper(),
    )
    db.add(order)
    for li in line_items:
        p = li["product"]
        db.add(OrderItem(
            order_id=oid, product_id=p.id, name=p.name,
            size=li["size"], qty=li["qty"], price=li["price"],
        ))
        # decrement stock (best effort)
        p.stock = max(0, (p.stock or 0) - li["qty"])
    db.commit()
    db.refresh(order)

    # fire-and-forget order email
    try:
        send_order_email(db, order)
    except Exception:  # noqa: BLE001
        pass
    return order


# ---------------- Admin ----------------
@router.get("/api/admin/orders")
def list_orders(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    status: str | None = Query(None),
):
    q = db.query(Order).order_by(Order.created_at.desc())
    if status:
        q = q.filter(Order.status == status)
    return [OrderOut.model_validate(o) for o in q.all()]


@router.get("/api/admin/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


@router.put("/api/admin/orders/{order_id}/status", response_model=OrderOut)
def update_status(
    order_id: str,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if data.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.status = data.status
    db.commit()
    db.refresh(o)
    return o


@router.get("/api/admin/stats")
def stats(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    orders = db.query(Order).all()
    revenue = sum(o.total for o in orders if o.status != "cancelled")
    by_status = {}
    for o in orders:
        by_status[o.status] = by_status.get(o.status, 0) + 1
    return {
        "orders": len(orders),
        "revenue": revenue,
        "products": db.query(Product).count(),
        "low_stock": db.query(Product).filter(Product.stock <= 5).count(),
        "by_status": by_status,
    }
