"""Transactional email via Resend.

Falls back to log-only mode when ``RESEND_API_KEY`` is empty. Emails are
still persisted to the ``email_log`` collection so admins can see the queue
in MOCKED mode.
"""
from __future__ import annotations
import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    import resend
except Exception:
    resend = None

logger = logging.getLogger("mypay.email")


def _is_live() -> bool:
    key = (os.environ.get("RESEND_API_KEY") or "").strip()
    return bool(key) and resend is not None


def _format_money(n: float) -> str:
    return "${:,.0f}".format(n)


def render(template: str, ctx: Dict) -> Dict[str, str]:
    """Return {subject, html} for a given template id."""
    if template == "disbursement_confirmation":
        return {
            "subject": f"Funds wired · {_format_money(ctx['advance_amount'])} for {ctx['brand_name']}",
            "html": _shell(
                f"""
                <p style="font-family: 'Instrument Serif', serif; font-size:40px; margin:0 0 12px 0;">Your advance is on the way.</p>
                <p style="margin:0 0 24px 0; color:#52525B;">Deal <b>{ctx['deal_title']}</b> — {ctx['brand_name']} — Net {ctx['payment_terms_days']}</p>
                <table width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #E4E4E7; border-bottom:1px solid #E4E4E7;">
                  <tr><td style="padding:14px 0; color:#52525B;">Advance (to you)</td><td align="right" style="font-family:monospace;">{_format_money(ctx['advance_amount'])}</td></tr>
                  <tr><td style="padding:14px 0; color:#52525B;">Discount fee</td><td align="right" style="font-family:monospace;">{_format_money(ctx['discount_fee'])}</td></tr>
                  <tr><td style="padding:14px 0; color:#52525B;">Brand pays at maturity</td><td align="right" style="font-family:monospace;">{_format_money(ctx['deal_amount'])}</td></tr>
                  <tr><td style="padding:14px 0; color:#52525B;">Maturity date</td><td align="right" style="font-family:monospace;">{ctx.get('maturity_date', '—')}</td></tr>
                </table>
                <p style="margin:24px 0 8px 0; color:#52525B;">Funds typically appear in 2–4 hours.</p>
                """,
                ctx
            ),
        }
    if template == "maturity_reminder":
        return {
            "subject": f"Maturity in {ctx['days_to_maturity']} days · {ctx['brand_name']}",
            "html": _shell(
                f"""
                <p style="font-family: 'Instrument Serif', serif; font-size:40px; margin:0 0 12px 0;">Invoice matures in {ctx['days_to_maturity']} days.</p>
                <p style="color:#52525B;">We&#39;ll auto-collect {_format_money(ctx['deal_amount'])} from {ctx['brand_name']} on <b>{ctx['maturity_date']}</b>.</p>
                <p style="color:#52525B;">No action needed on your side. If the brand prefers to pay early, share this link:</p>
                <p><a href="{ctx.get('pay_url', '#')}" style="display:inline-block; background:#0A0A0A; color:#fff; padding:12px 20px; font-weight:500; text-decoration:none;">Brand pay link</a></p>
                """, ctx
            ),
        }
    if template == "repayment_received":
        return {
            "subject": f"Repaid · {_format_money(ctx['advance_amount'])} credit recycled",
            "html": _shell(
                f"""
                <p style="font-family: 'Instrument Serif', serif; font-size:40px; margin:0 0 12px 0;">Settled. Credit recycled.</p>
                <p style="color:#52525B;">{ctx['brand_name']} just paid the <b>{_format_money(ctx['deal_amount'])}</b> invoice in full.</p>
                <p style="color:#52525B;"><b>{_format_money(ctx['advance_amount'])}</b> is back in your revolving limit.</p>
                """, ctx
            ),
        }
    raise ValueError(f"Unknown template {template}")


def _shell(inner: str, ctx: Dict) -> str:
    return f"""
    <html><body style="margin:0; padding:32px; background:#FAFAFA; font-family:Helvetica,Arial,sans-serif;">
      <div style="max-width:560px; margin:0 auto; background:#fff; border:1px solid #E4E4E7; padding:32px;">
        <div style="font-family:'Instrument Serif', serif; font-size:28px; border-bottom:1px solid #E4E4E7; padding-bottom:16px; margin-bottom:24px;">My Pay <span style="font-size:10px; letter-spacing:0.2em; color:#A1A1AA; text-transform:uppercase;">/ creator receivables</span></div>
        {inner}
        <div style="font-family:monospace; font-size:10px; color:#A1A1AA; margin-top:32px; border-top:1px solid #E4E4E7; padding-top:16px;">
          Ref {ctx.get('deal_id','—')[:8].upper()} · Sent {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        </div>
      </div>
    </body></html>
    """


async def send_notification(*, db, to: str, template: str, ctx: Dict) -> Dict:
    """Persist + send. Always writes to email_log for audit."""
    rendered = render(template, ctx)
    now = datetime.now(timezone.utc).isoformat()
    log_id = str(uuid.uuid4())
    record = {
        "id": log_id,
        "to": to,
        "template": template,
        "subject": rendered["subject"],
        "ctx": {k: v for k, v in ctx.items() if isinstance(v, (str, int, float, bool))},
        "provider": "resend" if _is_live() else "mock",
        "status": "queued",
        "created_at": now,
    }
    await db.email_log.insert_one(record)

    sender = os.environ.get("SENDER_EMAIL") or "notifications@mypay.io"
    try:
        if _is_live():
            resend.api_key = os.environ["RESEND_API_KEY"]
            params = {
                "from": sender,
                "to": [to],
                "subject": rendered["subject"],
                "html": rendered["html"],
            }
            r = await asyncio.to_thread(resend.Emails.send, params)
            await db.email_log.update_one({"id": log_id}, {"$set": {"status": "sent", "provider_id": (r or {}).get("id"), "sent_at": datetime.now(timezone.utc).isoformat()}})
            return {"ok": True, "provider": "resend", "id": (r or {}).get("id"), "log_id": log_id}
        else:
            logger.info(f"[MOCK EMAIL] to={to} template={template} subject={rendered['subject']}")
            await db.email_log.update_one({"id": log_id}, {"$set": {"status": "mocked", "sent_at": datetime.now(timezone.utc).isoformat()}})
            return {"ok": True, "provider": "mock", "log_id": log_id}
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        await db.email_log.update_one({"id": log_id}, {"$set": {"status": "error", "error": str(e)[:300]}})
        return {"ok": False, "error": str(e), "log_id": log_id}


async def list_log(db, limit: int = 50) -> List[Dict]:
    return await db.email_log.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
