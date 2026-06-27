"""Influencer & Referral program — admin management + public referral tracking."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..database import get_db
from ..models import AdminUser, Influencer, ReferralOrder, ReferralVisit
from ..schemas import InfluencerIn
from ..utils import slugify

router = APIRouter(tags=["influencer"])


# ───────────────────────────── Public ─────────────────────────────

@router.get("/api/referral/{code}")
def track_referral(code: str, request: Request, db: Session = Depends(get_db)):
    inf = db.query(Influencer).filter(Influencer.referral_code == code, Influencer.status == "approved").first()
    if not inf:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    inf.total_clicks = (inf.total_clicks or 0) + 1
    db.add(ReferralVisit(
        influencer_id=inf.id,
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", "")[:255],
    ))
    db.commit()
    return {
        "ok": True,
        "coupon_code": inf.coupon_code,
        "influencer_name": inf.name,
    }


# ───────────────────────────── Admin ─────────────────────────────

@router.get("/api/admin/influencers")
def list_influencers(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    infs = db.query(Influencer).order_by(Influencer.created_at.desc()).all()
    return [
        {
            "id": i.id, "name": i.name, "email": i.email, "phone": i.phone,
            "referral_code": i.referral_code, "referral_url": i.referral_url,
            "coupon_code": i.coupon_code, "commission_percent": i.commission_percent,
            "status": i.status,
            "total_clicks": i.total_clicks, "total_orders": i.total_orders,
            "total_revenue": i.total_revenue, "total_commission": i.total_commission,
            "paid_commission": i.paid_commission,
            "created_at": i.created_at.isoformat() if i.created_at else "",
        }
        for i in infs
    ]


@router.post("/api/admin/influencers")
def create_influencer(data: InfluencerIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    code = data.referral_code or slugify(data.name)
    if db.query(Influencer).filter(Influencer.referral_code == code).first():
        raise HTTPException(status_code=400, detail="Referral code already exists")
    inf = Influencer(
        name=data.name, email=data.email, phone=data.phone,
        referral_code=code, coupon_code=data.coupon_code,
        commission_percent=data.commission_percent,
        status=data.status,
    )
    db.add(inf)
    db.commit()
    db.refresh(inf)
    return {"ok": True, "id": inf.id, "referral_code": inf.referral_code}


@router.put("/api/admin/influencers/{inf_id}")
def update_influencer(inf_id: int, data: InfluencerIn, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    inf = db.query(Influencer).filter(Influencer.id == inf_id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    inf.name = data.name
    inf.email = data.email
    inf.phone = data.phone
    if data.referral_code and data.referral_code != inf.referral_code:
        if db.query(Influencer).filter(Influencer.referral_code == data.referral_code).first():
            raise HTTPException(status_code=400, detail="Referral code already exists")
        inf.referral_code = data.referral_code
    inf.coupon_code = data.coupon_code
    inf.commission_percent = data.commission_percent
    inf.status = data.status
    db.commit()
    return {"ok": True}


@router.delete("/api/admin/influencers/{inf_id}")
def delete_influencer(inf_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    inf = db.query(Influencer).filter(Influencer.id == inf_id).first()
    if inf:
        db.delete(inf)
        db.commit()
    return {"ok": True}


@router.get("/api/admin/influencers/{inf_id}/stats")
def influencer_stats(inf_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    inf = db.query(Influencer).filter(Influencer.id == inf_id).first()
    if not inf:
        raise HTTPException(status_code=404, detail="Influencer not found")
    orders = db.query(ReferralOrder).filter(ReferralOrder.influencer_id == inf_id).all()
    visits = db.query(ReferralVisit).filter(ReferralVisit.influencer_id == inf_id).count()
    return {
        "total_clicks": visits,
        "total_orders": len(orders),
        "total_revenue": sum(o.commission / (inf.commission_percent / 100) if inf.commission_percent else 0 for o in orders),
        "total_commission": sum(o.commission for o in orders),
        "paid_commission": sum(o.commission for o in orders if o.paid),
        "unpaid_commission": sum(o.commission for o in orders if not o.paid),
        "conversion_rate": round(len(orders) / max(visits, 1) * 100, 1),
    }
