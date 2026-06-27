"""Notification system — Email (Brevo) + WhatsApp + logs."""
import json

import requests
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Notification, Order
from .utils import get_settings


def _log_notification(db: Session, channel: str, recipient: str, event_type: str,
                      subject: str, status: str = "pending", error: str = ""):
    db.add(Notification(
        channel=channel, recipient=recipient, event_type=event_type,
        subject=subject, status=status, error=error,
    ))
    db.commit()


def send_brevo_email(api_key: str, from_email: str, from_name: str,
                     to_email: str, subject: str, html: str) -> bool:
    if not api_key or not to_email:
        return False
    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "sender": {"name": from_name, "email": from_email},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html,
            },
            timeout=15,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def send_whatsapp(api_url: str, api_key: str, phone: str, message: str) -> bool:
    if not api_url or not api_key or not phone:
        return False
    try:
        resp = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"phone": phone, "message": message},
            timeout=15,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def send_order_email(db: Session, order: Order):
    """Send order confirmation email + WhatsApp."""
    settings = get_settings(db)

    # Email
    if order.email:
        subject = f"Order Confirmation - {order.id} | PrimeNutra Wellness"
        items_html = ""
        for item in order.items:
            items_html += f"<tr><td>{item.name}</td><td>{item.qty}</td><td>₹{item.price:.0f}</td></tr>"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1b6b3c; color: white; padding: 20px; text-align: center;">
                <h1>🌿 PrimeNutra Wellness</h1>
            </div>
            <div style="padding: 20px;">
                <h2>Order Confirmed!</h2>
                <p>Hi {order.customer_name},</p>
                <p>Thank you for your order. Here's your order summary:</p>
                <p><strong>Order ID:</strong> {order.id}</p>
                <p><strong>Invoice:</strong> {order.invoice_number}</p>
                <table border="1" cellpadding="8" cellspacing="0" style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #f0f0f0;"><th>Item</th><th>Qty</th><th>Price</th></tr>
                    {items_html}
                </table>
                <p style="margin-top: 12px;">
                    <strong>Subtotal:</strong> ₹{order.subtotal:.0f}<br>
                    <strong>Discount:</strong> -₹{order.discount:.0f}<br>
                    <strong>Shipping:</strong> ₹{order.shipping:.0f}<br>
                    <strong>Tax:</strong> ₹{order.tax_amount:.0f}<br>
                    <strong>Total:</strong> ₹{order.total:.0f}
                </p>
                <p><strong>Payment:</strong> {order.payment_method}</p>
                <p><strong>Delivery Address:</strong><br>{order.address}, {order.city}, {order.state} - {order.pincode}</p>
                <p>We'll notify you when your order ships!</p>
            </div>
            <div style="background: #f0f0f0; padding: 10px; text-align: center; font-size: 12px;">
                PrimeNutra Wellness | primenutrawellness.in
            </div>
        </div>
        """
        sent = send_brevo_email(
            settings.get("brevo_api_key", ""),
            settings.get("brevo_from_email", "care@primenutrawellness.in"),
            settings.get("brevo_from_name", "PrimeNutra Wellness"),
            order.email, subject, html,
        )
        _log_notification(
            db, "email", order.email, "order_confirmation",
            subject, "sent" if sent else "failed",
        )

    # WhatsApp
    wa_url = settings.get("whatsapp_api_url", "")
    wa_key = settings.get("whatsapp_api_key", "")
    if order.phone and wa_url:
        msg = (
            f"🌿 *PrimeNutra Wellness*\n\n"
            f"✅ Order Confirmed!\n"
            f"Order: {order.id}\n"
            f"Total: ₹{order.total:.0f}\n"
            f"Payment: {order.payment_method}\n\n"
            f"Track: https://primenutrawellness.in/track.html?id={order.id}"
        )
        sent = send_whatsapp(wa_url, wa_key, order.phone, msg)
        _log_notification(
            db, "whatsapp", order.phone, "order_confirmation",
            f"Order {order.id}", "sent" if sent else "failed",
        )


def send_dispatch_notification(db: Session, order: Order):
    """Notify customer when order is dispatched."""
    settings = get_settings(db)

    if order.email:
        subject = f"Your Order {order.id} Has Been Shipped! | PrimeNutra Wellness"
        tracking_info = ""
        if order.tracking_url:
            tracking_info = f'<p><a href="{order.tracking_url}">Track Your Package</a></p>'
        elif order.tracking_number:
            tracking_info = f"<p>Tracking Number: {order.tracking_number}</p>"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1b6b3c; color: white; padding: 20px; text-align: center;">
                <h1>🌿 PrimeNutra Wellness</h1>
            </div>
            <div style="padding: 20px;">
                <h2>📦 Your Order Has Shipped!</h2>
                <p>Hi {order.customer_name},</p>
                <p>Great news! Your order <strong>{order.id}</strong> has been dispatched.</p>
                <p><strong>Courier:</strong> {order.courier or 'Standard Delivery'}</p>
                {tracking_info}
                {f'<p><strong>Estimated Delivery:</strong> {order.estimated_delivery.strftime("%d %b %Y") if order.estimated_delivery else "3-5 business days"}</p>'}
            </div>
        </div>
        """
        sent = send_brevo_email(
            settings.get("brevo_api_key", ""),
            settings.get("brevo_from_email", "care@primenutrawellness.in"),
            settings.get("brevo_from_name", "PrimeNutra Wellness"),
            order.email, subject, html,
        )
        _log_notification(db, "email", order.email, "dispatch", subject, "sent" if sent else "failed")

    wa_url = settings.get("whatsapp_api_url", "")
    wa_key = settings.get("whatsapp_api_key", "")
    if order.phone and wa_url:
        msg = (
            f"📦 *Order Shipped!*\n\n"
            f"Order: {order.id}\n"
            f"Courier: {order.courier or 'Standard'}\n"
            f"Tracking: {order.tracking_number or 'Will be updated shortly'}\n"
            f"Track: {order.tracking_url or f'https://primenutrawellness.in/track.html?id={order.id}'}"
        )
        sent = send_whatsapp(wa_url, wa_key, order.phone, msg)
        _log_notification(db, "whatsapp", order.phone, "dispatch", f"Order {order.id} shipped", "sent" if sent else "failed")
