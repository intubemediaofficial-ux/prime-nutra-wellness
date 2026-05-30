"""Best-effort transactional email via Brevo (Sendinblue). Never raises to caller."""
import requests
from sqlalchemy.orm import Session

from .config import BREVO_API_KEY
from .utils import get_settings


def send_order_email(db: Session, order) -> bool:
    settings = get_settings(db)
    api_key = settings.get("brevo_api_key") or BREVO_API_KEY
    if not api_key or not order.email:
        return False
    from_email = settings.get("brevo_from_email") or "care@primenutrawellness.in"
    from_name = settings.get("brevo_from_name") or settings.get("store_name") or "PrimeNutra Wellness"

    rows = "".join(
        f"<tr><td style='padding:6px 0'>{it.name} ({it.size}) ×{it.qty}</td>"
        f"<td style='text-align:right'>₹{it.price * it.qty:.0f}</td></tr>"
        for it in order.items
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1b5e34">Thank you for your order! 🌿</h2>
      <p>Hi {order.customer_name}, we've received your order <b>#{order.id}</b>.</p>
      <table style="width:100%;border-collapse:collapse">{rows}</table>
      <hr>
      <p style="text-align:right">Subtotal: ₹{order.subtotal:.0f}<br>
      Discount: − ₹{order.discount:.0f}<br>
      <b>Total: ₹{order.total:.0f}</b> ({order.payment_method})</p>
      <p>We'll contact you at {order.phone} to confirm delivery.</p>
      <p style="color:#777">— {from_name}</p>
    </div>"""

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "content-type": "application/json"},
            json={
                "sender": {"email": from_email, "name": from_name},
                "to": [{"email": order.email, "name": order.customer_name}],
                "subject": f"Order #{order.id} confirmed – {from_name}",
                "htmlContent": html,
            },
            timeout=10,
        )
        return resp.status_code in (200, 201)
    except requests.RequestException:
        return False
