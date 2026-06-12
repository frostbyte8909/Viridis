import smtplib
from email.message import EmailMessage
import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def _send_email_sync(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.warning("SMTP host not configured. Skipping email alert.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user or "no-reply@viridis.local"
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info(f"Alert email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")

async def send_webhook_alert(tenant_id: str, threshold: str, details: dict) -> None:
    if not settings.alert_webhook_url:
        return
        
    payload = {
        "tenant_id": tenant_id,
        "alert_type": "quota_warning" if threshold == "80" else "quota_exceeded",
        "threshold_percentage": threshold,
        "details": details
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.alert_webhook_url, json=payload, timeout=5.0)
            response.raise_for_status()
            logger.info(f"Webhook alert triggered for tenant {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to trigger webhook alert: {e}")

async def dispatch_quota_alert(tenant_id: str, email: str, threshold: str, current_usage: int, limit: int) -> None:
    """
    Dispatches notifications via configured channels.
    Run via asyncio.create_task() to avoid blocking request enforcement.
    """
    subject = f"[Viridis Alert] Quota {threshold}% Reached for Tenant {tenant_id}"
    body = f"Tenant {tenant_id} has reached {threshold}% of their API rate limit quota.\nCurrent Usage: {current_usage} / {limit}"
    
    tasks = []
    if email and settings.smtp_host:
        tasks.append(asyncio.to_thread(_send_email_sync, email, subject, body))
        
    if settings.alert_webhook_url:
        details = {"current_usage": current_usage, "limit": limit}
        tasks.append(send_webhook_alert(tenant_id, threshold, details))
        
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
