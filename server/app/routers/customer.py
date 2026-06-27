"""Customer dashboard — wishlist, cart sync, orders, recently viewed, reviews, returns."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_customer
from ..database import get_db
from ..models import (
    CartItem, Customer, Order, Product, RecentlyViewed,
    ReturnRequest, Review, WishlistItem,
)
from ..schemas import CartItemIn, CartSyncIn, OrderOut, ReturnRequestIn, ReviewIn

router = APIRouter(prefix="/api/customer", tags=["customer"])


# ───────────────────────────── Wishlist ─────────────────────────────

@router.get("/wishlist")
def get_wishlist(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    items = (
        db.query(WishlistItem)
        .filter(WishlistItem.customer_id == customer.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    result = []
    for w in items:
        p = db.query(Product).filter(Product.id == w.product_id).first()
        result.append({
            "product_id": w.product_id,
            "product_name": p.name if p else w.product_id,
            "added_at": w.created_at.isoformat() if w.created_at else "",
        })
    return result


@router.post("/wishlist/{product_id}")
def add_to_wishlist(product_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    existing = db.query(WishlistItem).filter(
        WishlistItem.customer_id == customer.id, WishlistItem.product_id == product_id
    ).first()
    if existing:
        return {"ok": True, "message": "Already in wishlist"}
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    db.add(WishlistItem(customer_id=customer.id, product_id=product_id))
    db.commit()
    return {"ok": True}


@router.delete("/wishlist/{product_id}")
def remove_from_wishlist(product_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    item = db.query(WishlistItem).filter(
        WishlistItem.customer_id == customer.id, WishlistItem.product_id == product_id
    ).first()
    if item:
        db.delete(item)
        db.commit()
    return {"ok": True}


@router.post("/wishlist/{product_id}/move-to-cart")
def move_to_cart(product_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    # Add to cart
    existing_cart = db.query(CartItem).filter(
        CartItem.customer_id == customer.id, CartItem.product_id == product_id
    ).first()
    if existing_cart:
        existing_cart.qty += 1
    else:
        db.add(CartItem(customer_id=customer.id, product_id=product_id, qty=1))
    # Remove from wishlist
    item = db.query(WishlistItem).filter(
        WishlistItem.customer_id == customer.id, WishlistItem.product_id == product_id
    ).first()
    if item:
        db.delete(item)
    db.commit()
    return {"ok": True}


# ───────────────────────────── Cart Sync ─────────────────────────────

@router.get("/cart")
def get_cart(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    items = db.query(CartItem).filter(CartItem.customer_id == customer.id).all()
    return [
        {"id": c.product_id, "size": c.size, "qty": c.qty, "variant_index": c.variant_index}
        for c in items
    ]


@router.post("/cart/sync")
def sync_cart(data: CartSyncIn, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    """Replace server cart with client cart (merge strategy: client wins)."""
    db.query(CartItem).filter(CartItem.customer_id == customer.id).delete()
    for item in data.items:
        if item.qty > 0:
            db.add(CartItem(
                customer_id=customer.id,
                product_id=item.id,
                size=item.size,
                qty=item.qty,
                variant_index=item.variant_index,
            ))
    db.commit()
    return {"ok": True}


@router.post("/cart/add")
def add_to_cart_api(data: CartItemIn, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    existing = db.query(CartItem).filter(
        CartItem.customer_id == customer.id,
        CartItem.product_id == data.id,
        CartItem.size == data.size,
    ).first()
    if existing:
        existing.qty += data.qty
    else:
        db.add(CartItem(customer_id=customer.id, product_id=data.id, size=data.size, qty=data.qty, variant_index=data.variant_index))
    db.commit()
    return {"ok": True}


@router.put("/cart/{product_id}")
def update_cart_item(product_id: str, data: CartItemIn, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(
        CartItem.customer_id == customer.id, CartItem.product_id == product_id, CartItem.size == data.size
    ).first()
    if item:
        if data.qty <= 0:
            db.delete(item)
        else:
            item.qty = data.qty
        db.commit()
    return {"ok": True}


@router.delete("/cart/{product_id}")
def remove_from_cart(product_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    db.query(CartItem).filter(
        CartItem.customer_id == customer.id, CartItem.product_id == product_id
    ).delete()
    db.commit()
    return {"ok": True}


# ───────────────────────────── Orders ─────────────────────────────

@router.get("/orders")
def my_orders(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/orders/{order_id}", response_model=OrderOut)
def my_order_detail(order_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id, Order.customer_id == customer.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ───────────────────────────── Recently Viewed ─────────────────────────────

@router.get("/recently-viewed")
def get_recently_viewed(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    items = (
        db.query(RecentlyViewed)
        .filter(RecentlyViewed.customer_id == customer.id)
        .order_by(RecentlyViewed.viewed_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for r in items:
        p = db.query(Product).filter(Product.id == r.product_id).first()
        result.append({
            "product_id": r.product_id,
            "product_name": p.name if p else r.product_id,
            "viewed_at": r.viewed_at.isoformat() if r.viewed_at else "",
        })
    return result


@router.post("/recently-viewed/{product_id}")
def add_recently_viewed(product_id: str, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    existing = db.query(RecentlyViewed).filter(
        RecentlyViewed.customer_id == customer.id, RecentlyViewed.product_id == product_id
    ).first()
    if existing:
        existing.viewed_at = datetime.utcnow()
    else:
        db.add(RecentlyViewed(customer_id=customer.id, product_id=product_id))
        # Keep only last 30
        all_rv = (
            db.query(RecentlyViewed)
            .filter(RecentlyViewed.customer_id == customer.id)
            .order_by(RecentlyViewed.viewed_at.desc())
            .all()
        )
        if len(all_rv) > 30:
            for old in all_rv[30:]:
                db.delete(old)
    db.commit()
    return {"ok": True}


# ───────────────────────────── Reviews ─────────────────────────────

@router.post("/reviews")
def submit_review(data: ReviewIn, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == data.product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    # Check if already reviewed
    existing = db.query(Review).filter(
        Review.customer_id == customer.id, Review.product_id == data.product_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")
    # Check verified purchase
    verified = False
    if data.order_id:
        order = db.query(Order).filter(Order.id == data.order_id, Order.customer_id == customer.id).first()
        verified = order is not None and order.status == "delivered"
    review = Review(
        product_id=data.product_id,
        customer_id=customer.id,
        order_id=data.order_id,
        rating=max(1, min(5, data.rating)),
        title=data.title,
        body=data.body,
        images=data.images,
        verified_purchase=verified,
        approved=False,
    )
    db.add(review)
    db.commit()
    return {"ok": True, "message": "Review submitted for moderation"}


@router.get("/reviews")
def my_reviews(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    reviews = db.query(Review).filter(Review.customer_id == customer.id).order_by(Review.created_at.desc()).all()
    return [
        {
            "id": r.id, "product_id": r.product_id, "rating": r.rating,
            "title": r.title, "body": r.body, "approved": r.approved,
            "created_at": r.created_at.isoformat(),
        }
        for r in reviews
    ]


# ───────────────────────────── Return Requests ─────────────────────────────

@router.post("/returns")
def request_return(data: ReturnRequestIn, customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == data.order_id, Order.customer_id == customer.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ("delivered",):
        raise HTTPException(status_code=400, detail="Return only allowed for delivered orders")
    existing = db.query(ReturnRequest).filter(ReturnRequest.order_id == data.order_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Return request already exists")
    rr = ReturnRequest(
        order_id=data.order_id,
        customer_id=customer.id,
        reason=data.reason,
        images=data.images,
    )
    db.add(rr)
    db.commit()
    return {"ok": True, "message": "Return request submitted"}


@router.get("/returns")
def my_returns(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    returns = db.query(ReturnRequest).filter(ReturnRequest.customer_id == customer.id).order_by(ReturnRequest.created_at.desc()).all()
    return [
        {
            "id": r.id, "order_id": r.order_id, "reason": r.reason,
            "status": r.status, "refund_amount": r.refund_amount,
            "refund_method": r.refund_method or "",
            "created_at": r.created_at.isoformat(),
        }
        for r in returns
    ]
