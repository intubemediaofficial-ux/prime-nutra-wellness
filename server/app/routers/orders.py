"""Orders — checkout, admin order management, status tracking, invoices."""
import io
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..auth import get_current_admin, get_optional_customer
from ..database import get_db
from ..models import (
    AdminUser, Coupon, CouponUsage, Customer, InventoryLog,
    Order, OrderItem, OrderStatusLog, Product, ReturnRequest,
)
from ..schemas import (
    CheckoutIn, OrderOut, ReturnUpdateIn, ShippingUpdate, StatusUpdate,
)
from ..utils import get_settings, set_setting
from ..emailer import send_order_email

router = APIRouter(tags=["orders"])

ORDER_STATUSES = [
    "placed", "confirmed", "packed", "shipped", "in_transit",
    "out_for_delivery", "delivered", "cancelled", "returned", "refunded",
]


def _compute_tax(price: float, qty: int, gst_rate: float, seller_state: str, buyer_state: str):
    """Compute CGST/SGST (intra-state) or IGST (inter-state)."""
    taxable = price * qty
    tax = round(taxable * gst_rate / 100, 2)
    if seller_state and buyer_state and seller_state.lower() == buyer_state.lower():
        return {"cgst": round(tax / 2, 2), "sgst": round(tax / 2, 2), "igst": 0, "tax": tax}
    return {"cgst": 0, "sgst": 0, "igst": tax, "tax": tax}


def compute_order(db: Session, data: CheckoutIn):
    """Return (subtotal, discount, shipping, tax, total, line_items)."""
    settings = get_settings(db)
    seller_state = settings.get("company_state", "")
    line_items = []
    subtotal = 0.0
    total_tax = 0.0

    for ci in data.items:
        p = db.query(Product).filter(Product.id == ci.id, Product.active == True).first()
        if not p:
            raise HTTPException(status_code=400, detail=f"Product unavailable: {ci.id}")
        qty = max(1, int(ci.qty))
        line_total = p.price * qty
        subtotal += line_total

        tax_info = _compute_tax(p.price, qty, p.gst_rate, seller_state, data.state)
        total_tax += tax_info["tax"]

        line_items.append({
            "product": p, "size": ci.size, "qty": qty, "price": p.price,
            "tax_info": tax_info,
        })

    # automatic discount tiers
    discount = 0.0
    if subtotal >= 1599:
        discount = round(subtotal * 0.12)
    elif subtotal >= 1299:
        discount = round(subtotal * 0.10)
    elif subtotal >= 999:
        discount = round(subtotal * 0.08)

    # coupon
    code = (data.coupon_code or "").strip().upper()
    if code:
        c = db.query(Coupon).filter(Coupon.code == code, Coupon.active == True).first()
        if c and subtotal >= (c.min_order or 0) and (not c.expires_at or c.expires_at >= datetime.utcnow()):
            if c.usage_limit and c.used_count >= c.usage_limit:
                pass  # coupon exhausted
            elif c.type == "free_shipping":
                discount = max(discount, 0)
            else:
                cdisc = subtotal * (c.value / 100) if c.type == "percent" else c.value
                if c.max_discount and cdisc > c.max_discount:
                    cdisc = c.max_discount
                discount = max(discount, round(min(cdisc, subtotal)))

    threshold = float(settings.get("free_ship_threshold", "0") or 0)
    fee = float(settings.get("shipping_fee", "0") or 0)
    shipping = 0.0 if (threshold and subtotal >= threshold) or fee == 0 else fee

    # COD charge
    cod_charge = 0.0
    if data.payment_method == "COD":
        cod_charge = float(settings.get("cod_charge", "0") or 0)

    total = max(0, subtotal - discount + shipping + cod_charge)
    return subtotal, discount, shipping, total_tax, total, line_items, code


@router.post("/api/checkout/quote")
def quote(data: CheckoutIn, db: Session = Depends(get_db)):
    subtotal, discount, shipping, tax, total, _, _ = compute_order(db, data)
    return {"subtotal": subtotal, "coupon_discount": discount, "shipping": shipping, "tax_amount": tax, "total": total}


@router.post("/api/orders", response_model=OrderOut)
def place_order(
    data: CheckoutIn,
    db: Session = Depends(get_db),
    customer: Customer | None = Depends(get_optional_customer),
):
    if not data.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    settings = get_settings(db)
    method = data.payment_method if data.payment_method in {"COD", "Razorpay", "Partial"} else "COD"

    if method == "COD" and settings.get("cod_enabled", "true") != "true":
        raise HTTPException(status_code=400, detail="COD is currently disabled")

    # COD rules
    if method == "COD":
        cod_min = float(settings.get("cod_min_order", "0") or 0)
        cod_max = float(settings.get("cod_max_order", "0") or 0)
        subtotal_check = 0
        for ci in data.items:
            p = db.query(Product).filter(Product.id == ci.id).first()
            if p:
                subtotal_check += (p.price or 0) * ci.qty
        if cod_min and subtotal_check < cod_min:
            raise HTTPException(status_code=400, detail=f"Minimum order for COD is ₹{cod_min}")
        if cod_max and subtotal_check > cod_max:
            raise HTTPException(status_code=400, detail=f"Maximum order for COD is ₹{cod_max}")

    subtotal, discount, shipping, tax, total, line_items, coupon_code = compute_order(db, data)
    oid = "PNW" + str(int(time.time() * 1000))[-9:]

    # Partial payment
    partial_paid = 0.0
    partial_remaining = 0.0
    if method == "Partial" and settings.get("partial_payment_enabled") == "true":
        partial_paid = max(float(settings.get("partial_min_advance", "500")), data.partial_amount)
        partial_remaining = total - partial_paid
        method = "Partial"

    # Generate invoice number
    inv_prefix = settings.get("invoice_prefix", "INV")
    inv_counter = int(settings.get("invoice_counter", "0") or 0) + 1
    set_setting(db, "invoice_counter", str(inv_counter))
    invoice_number = f"{inv_prefix}-{inv_counter:06d}"

    seller_state = settings.get("company_state", "")
    total_cgst = sum(li["tax_info"]["cgst"] for li in line_items)
    total_sgst = sum(li["tax_info"]["sgst"] for li in line_items)
    total_igst = sum(li["tax_info"]["igst"] for li in line_items)

    order = Order(
        id=oid,
        customer_id=customer.id if customer else None,
        customer_name=data.customer_name,
        phone=data.phone,
        email=data.email,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        landmark=data.landmark,
        gst_number=data.gst_number,
        order_notes=data.order_notes,
        payment_method=method,
        payment_status="pending",
        status="placed",
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        tax_amount=tax,
        cgst=total_cgst,
        sgst=total_sgst,
        igst=total_igst,
        total=total,
        coupon_code=coupon_code,
        partial_paid=partial_paid,
        partial_remaining=partial_remaining,
        invoice_number=invoice_number,
    )
    db.add(order)

    # Status log
    db.add(OrderStatusLog(order_id=oid, status="placed", note="Order placed"))

    for li in line_items:
        p = li["product"]
        db.add(OrderItem(
            order_id=oid, product_id=p.id, name=p.name,
            size=li["size"], qty=li["qty"], price=li["price"],
            mrp=p.mrp, sku=p.sku or "", hsn_code=p.hsn_code or "",
            gst_rate=p.gst_rate, tax_amount=li["tax_info"]["tax"],
        ))
        p.stock = max(0, (p.stock or 0) - li["qty"])
        db.add(InventoryLog(
            product_id=p.id, change=-li["qty"],
            reason="sale", note=f"Order {oid}",
        ))

    # Track coupon usage
    if coupon_code:
        c = db.query(Coupon).filter(Coupon.code == coupon_code).first()
        if c:
            c.used_count = (c.used_count or 0) + 1
            db.add(CouponUsage(
                coupon_code=coupon_code,
                customer_id=customer.id if customer else None,
                order_id=oid,
            ))

    db.commit()
    db.refresh(order)

    try:
        send_order_email(db, order)
    except Exception:
        pass
    return order


# ───────────────────────────── Admin ─────────────────────────────

@router.get("/api/admin/orders")
def list_orders(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    status: str | None = Query(None),
    search: str | None = Query(None),
):
    q = db.query(Order).order_by(Order.created_at.desc())
    if status:
        q = q.filter(Order.status == status)
    if search:
        s = f"%{search}%"
        q = q.filter(
            (Order.id.ilike(s)) | (Order.customer_name.ilike(s)) | (Order.phone.ilike(s))
        )
    return [OrderOut.model_validate(o) for o in q.all()]


@router.get("/api/admin/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


@router.put("/api/admin/orders/{order_id}/status", response_model=OrderOut)
def update_status(
    order_id: str, data: StatusUpdate,
    db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    if data.status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    o.status = data.status
    if data.status == "delivered":
        o.delivered_at = datetime.utcnow()
        o.payment_status = "paid" if o.payment_method != "COD" else o.payment_status
    if data.status == "cancelled":
        # Restore stock
        for item in o.items:
            p = db.query(Product).filter(Product.id == item.product_id).first()
            if p:
                p.stock = (p.stock or 0) + item.qty
                db.add(InventoryLog(product_id=p.id, change=item.qty, reason="cancellation", note=f"Order {order_id} cancelled"))
    db.add(OrderStatusLog(order_id=order_id, status=data.status, note=data.note))
    db.commit()
    db.refresh(o)
    return o


@router.put("/api/admin/orders/{order_id}/shipping")
def update_shipping(
    order_id: str, data: ShippingUpdate,
    db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if data.courier:
        o.courier = data.courier
    if data.tracking_number:
        o.tracking_number = data.tracking_number
    if data.tracking_url:
        o.tracking_url = data.tracking_url
    if data.dispatch_date:
        o.dispatch_date = data.dispatch_date
    if data.estimated_delivery:
        o.estimated_delivery = data.estimated_delivery
    db.commit()
    return {"ok": True}


# ───────────────────────────── Admin Returns ─────────────────────────────

@router.get("/api/admin/returns")
def list_returns(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    returns = db.query(ReturnRequest).order_by(ReturnRequest.created_at.desc()).all()
    return [
        {
            "id": r.id, "order_id": r.order_id, "customer_id": r.customer_id,
            "reason": r.reason, "images": r.images, "status": r.status,
            "refund_amount": r.refund_amount, "refund_method": r.refund_method,
            "admin_notes": r.admin_notes,
            "created_at": r.created_at.isoformat(),
        }
        for r in returns
    ]


@router.put("/api/admin/returns/{return_id}")
def update_return(
    return_id: int, data: ReturnUpdateIn,
    db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin),
):
    rr = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not rr:
        raise HTTPException(status_code=404, detail="Return request not found")
    rr.status = data.status
    rr.refund_amount = data.refund_amount
    rr.refund_method = data.refund_method
    rr.admin_notes = data.admin_notes
    if data.status in ("refunded", "partial_refunded"):
        order = db.query(Order).filter(Order.id == rr.order_id).first()
        if order:
            order.status = "refunded"
            db.add(OrderStatusLog(order_id=order.id, status="refunded", note=f"Refund ₹{data.refund_amount}"))
    db.commit()
    return {"ok": True}


# ───────────────────────────── Stats ─────────────────────────────

@router.get("/api/admin/stats")
def stats(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    orders = db.query(Order).all()
    revenue = sum(o.total for o in orders if o.status not in ("cancelled", "refunded"))
    by_status = {}
    for o in orders:
        by_status[o.status] = by_status.get(o.status, 0) + 1
    customers = db.query(Customer).count()
    return {
        "orders": len(orders),
        "revenue": revenue,
        "products": db.query(Product).count(),
        "low_stock": db.query(Product).filter(Product.stock <= 5).count(),
        "customers": customers,
        "returns": db.query(ReturnRequest).filter(ReturnRequest.status == "requested").count(),
        "by_status": by_status,
    }


# ───────────────────────────── Invoice PDF ─────────────────────────────

@router.get("/api/admin/orders/{order_id}/invoice")
def download_invoice(order_id: str, db: Session = Depends(get_db)):
    """Generate GST invoice PDF for an order."""
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    settings = get_settings(db)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph(f"<b>{settings.get('company_name', 'PrimeNutra Wellness')}</b>", styles["Title"]))
    if settings.get("company_address"):
        elements.append(Paragraph(settings["company_address"], styles["Normal"]))
    if settings.get("gst_number"):
        elements.append(Paragraph(f"GSTIN: {settings['gst_number']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"<b>TAX INVOICE</b>", styles["Heading2"]))
    elements.append(Paragraph(f"Invoice #: {o.invoice_number}", styles["Normal"]))
    elements.append(Paragraph(f"Order #: {o.id}", styles["Normal"]))
    elements.append(Paragraph(f"Date: {o.created_at.strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 8))

    # Customer
    elements.append(Paragraph(f"<b>Bill To:</b> {o.customer_name}", styles["Normal"]))
    elements.append(Paragraph(f"Phone: {o.phone}", styles["Normal"]))
    if o.address:
        elements.append(Paragraph(f"Address: {o.address}, {o.city}, {o.state} - {o.pincode}", styles["Normal"]))
    if o.gst_number:
        elements.append(Paragraph(f"GSTIN: {o.gst_number}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Items table
    table_data = [["#", "Item", "HSN", "Qty", "Rate", "GST%", "Tax", "Amount"]]
    for i, item in enumerate(o.items, 1):
        amt = item.price * item.qty
        table_data.append([
            str(i), item.name, item.hsn_code or "-", str(item.qty),
            f"₹{item.price:.0f}", f"{item.gst_rate:.0f}%",
            f"₹{item.tax_amount:.0f}", f"₹{amt:.0f}",
        ])

    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b6b3c")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Totals
    totals = [
        ["Subtotal", f"₹{o.subtotal:.0f}"],
        ["Discount", f"- ₹{o.discount:.0f}"],
        ["Shipping", f"₹{o.shipping:.0f}"],
    ]
    if o.cgst:
        totals.append(["CGST", f"₹{o.cgst:.0f}"])
    if o.sgst:
        totals.append(["SGST", f"₹{o.sgst:.0f}"])
    if o.igst:
        totals.append(["IGST", f"₹{o.igst:.0f}"])
    totals.append(["Total", f"₹{o.total:.0f}"])
    tt = Table(totals, colWidths=[120, 100])
    tt.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(tt)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Payment: {o.payment_method} ({o.payment_status})", styles["Normal"]))

    doc.build(elements)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{o.invoice_number}.pdf"},
    )


# ───────────────────────────── Order Tracking (public) ─────────────────────────────

@router.get("/api/orders/{order_id}/track")
def track_order(order_id: str, phone: str = Query(...), db: Session = Depends(get_db)):
    """Public tracking by order ID + phone."""
    o = db.query(Order).filter(Order.id == order_id, Order.phone == phone).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    logs = [
        {"status": s.status, "note": s.note, "created_at": s.created_at.isoformat()}
        for s in sorted(o.status_history, key=lambda x: x.created_at)
    ]
    return {
        "id": o.id,
        "status": o.status,
        "total": o.total,
        "payment_method": o.payment_method,
        "courier": o.courier,
        "tracking_number": o.tracking_number,
        "tracking_url": o.tracking_url,
        "dispatch_date": o.dispatch_date.isoformat() if o.dispatch_date else None,
        "estimated_delivery": o.estimated_delivery.isoformat() if o.estimated_delivery else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "status_logs": logs,
        "status_history": logs,
    }
