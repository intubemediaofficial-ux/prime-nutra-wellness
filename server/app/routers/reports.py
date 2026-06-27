"""Reports — revenue, orders, products, customers, inventory, GST."""
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import (
    AdminUser, Coupon, CouponUsage, Customer, InventoryLog,
    Order, OrderItem, Product, ReturnRequest,
)

router = APIRouter(prefix="/api/admin/reports", tags=["reports"])


@router.get("/revenue")
def revenue_report(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    orders = db.query(Order).filter(
        Order.created_at >= since, Order.status.notin_(["cancelled", "refunded"])
    ).all()

    total_revenue = sum(o.total for o in orders)
    total_orders = len(orders)
    avg_order = total_revenue / max(total_orders, 1)
    total_tax = sum(o.tax_amount for o in orders)
    total_discount = sum(o.discount for o in orders)

    # Daily breakdown
    daily = {}
    for o in orders:
        day = o.created_at.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"date": day, "orders": 0, "revenue": 0}
        daily[day]["orders"] += 1
        daily[day]["revenue"] += o.total

    return {
        "period_days": days,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": round(avg_order, 2),
        "total_tax": total_tax,
        "total_discount": total_discount,
        "daily": sorted(daily.values(), key=lambda x: x["date"]),
    }


@router.get("/products")
def product_report(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    items = (
        db.query(
            OrderItem.product_id,
            OrderItem.name,
            func.sum(OrderItem.qty).label("total_qty"),
            func.sum(OrderItem.price * OrderItem.qty).label("total_revenue"),
        )
        .join(Order)
        .filter(Order.created_at >= since, Order.status.notin_(["cancelled", "refunded"]))
        .group_by(OrderItem.product_id, OrderItem.name)
        .order_by(func.sum(OrderItem.qty).desc())
        .all()
    )
    return [
        {"product_id": i.product_id, "name": i.name, "qty_sold": i.total_qty, "revenue": float(i.total_revenue)}
        for i in items
    ]


@router.get("/customers")
def customer_report(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    customers = db.query(Customer).order_by(Customer.created_at.desc()).limit(100).all()
    result = []
    for c in customers:
        orders = db.query(Order).filter(Order.customer_id == c.id).all()
        result.append({
            "id": c.id, "name": c.name, "phone": c.phone, "email": c.email,
            "total_orders": len(orders),
            "total_spent": sum(o.total for o in orders if o.status not in ("cancelled", "refunded")),
            "created_at": c.created_at.isoformat() if c.created_at else "",
        })
    return result


@router.get("/inventory")
def inventory_report(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    products = db.query(Product).order_by(Product.stock.asc()).all()
    return [
        {
            "id": p.id, "name": p.name, "stock": p.stock,
            "low_stock_threshold": p.low_stock_threshold,
            "is_low": p.stock <= p.low_stock_threshold,
            "is_out": p.stock <= 0,
        }
        for p in products
    ]


@router.get("/coupons")
def coupon_report(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    coupons = db.query(Coupon).all()
    result = []
    for c in coupons:
        usages = db.query(CouponUsage).filter(CouponUsage.coupon_code == c.code).count()
        result.append({
            "code": c.code, "type": c.type, "value": c.value,
            "used_count": usages, "active": c.active,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        })
    return result


@router.get("/gst")
def gst_report(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    since = datetime.utcnow() - timedelta(days=days)
    orders = db.query(Order).filter(
        Order.created_at >= since, Order.status.notin_(["cancelled", "refunded"])
    ).all()
    total_cgst = sum(o.cgst for o in orders)
    total_sgst = sum(o.sgst for o in orders)
    total_igst = sum(o.igst for o in orders)
    total_tax = sum(o.tax_amount for o in orders)
    return {
        "period_days": days,
        "total_tax": total_tax,
        "cgst": total_cgst,
        "sgst": total_sgst,
        "igst": total_igst,
        "order_count": len(orders),
    }


@router.get("/export/{report_type}")
def export_report(
    report_type: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Export report as CSV."""
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)

    if report_type == "orders":
        since = datetime.utcnow() - timedelta(days=days)
        orders = db.query(Order).filter(Order.created_at >= since).order_by(Order.created_at.desc()).all()
        writer.writerow(["Order ID", "Date", "Customer", "Phone", "Status", "Payment", "Subtotal", "Discount", "Tax", "Total"])
        for o in orders:
            writer.writerow([o.id, o.created_at.strftime("%Y-%m-%d %H:%M"), o.customer_name, o.phone, o.status, o.payment_method, o.subtotal, o.discount, o.tax_amount, o.total])
    elif report_type == "products":
        products = db.query(Product).all()
        writer.writerow(["ID", "Name", "Category", "Price", "MRP", "Stock", "SKU", "Active"])
        for p in products:
            writer.writerow([p.id, p.name, p.category_id, p.price, p.mrp, p.stock, p.sku, p.active])
    elif report_type == "customers":
        customers = db.query(Customer).all()
        writer.writerow(["ID", "Name", "Phone", "Email", "Created"])
        for c in customers:
            writer.writerow([c.id, c.name, c.phone, c.email, c.created_at.strftime("%Y-%m-%d") if c.created_at else ""])
    elif report_type == "gst":
        since = datetime.utcnow() - timedelta(days=days)
        orders = db.query(Order).filter(Order.created_at >= since, Order.status.notin_(["cancelled", "refunded"])).all()
        writer.writerow(["Order ID", "Date", "Invoice", "Customer", "GSTIN", "Subtotal", "CGST", "SGST", "IGST", "Total Tax", "Total"])
        for o in orders:
            writer.writerow([o.id, o.created_at.strftime("%Y-%m-%d"), o.invoice_number, o.customer_name, o.gst_number, o.subtotal, o.cgst, o.sgst, o.igst, o.tax_amount, o.total])
    else:
        writer.writerow(["Error"])
        writer.writerow(["Unknown report type"])

    content = buf.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}-report.csv"},
    )
