"""AI-backed contract analysis using Claude Sonnet 4.5 via emergentintegrations."""
from __future__ import annotations
import os
import json
import logging
import uuid
from typing import Dict, Optional

logger = logging.getLogger("mypay.ai")

SYSTEM_PROMPT = (
    "You are a Senior Underwriter at a creator-economy invoice discounting firm. "
    "You analyse influencer brand deal contracts and return a STRICT JSON risk brief. "
    "Never include prose outside JSON. Be precise, use fintech terminology."
)


def _build_user_prompt(*, contract_text: str, deal_title: str, deal_amount: float,
                      brand_name: str, brand_tier: str) -> str:
    body = contract_text[:4000] if contract_text else "[no contract text provided — reason about deal metadata only]"
    return f"""Analyse the following brand deal for advance-rate underwriting.

BRAND: {brand_name} (tier: {brand_tier})
DEAL TITLE: {deal_title}
DEAL AMOUNT (USD): {deal_amount}
CONTRACT TEXT (may be partial, OCR-extracted or blank):
---
{body}
---

Return ONLY this JSON schema:
{{
  "verification_status": "verified" | "needs_review" | "rejected",
  "confidence_pct": 0-100,
  "key_terms": {{
    "deliverables": "short description",
    "payment_terms_days": number,
    "exclusivity": "none|category|full",
    "ip_rights": "brand|creator|shared",
    "kill_fee": "yes|no"
  }},
  "red_flags": ["short red flag 1", ...],
  "green_flags": ["short green flag 1", ...],
  "underwriter_note": "one-paragraph credit memo (<=60 words)"
}}
"""


def _parse_json_payload(text: str) -> Optional[Dict]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


async def _call_claude(prompt: str, api_key: str) -> Optional[str]:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=api_key,
        session_id=f"mypay-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    resp = await chat.send_message(UserMessage(text=prompt))
    return resp if isinstance(resp, str) else str(resp)


async def analyze_contract_with_ai(*, contract_text: str, deal_title: str, deal_amount: float,
                                    brand_name: str, brand_tier: str) -> Dict:
    """Ask Claude Sonnet 4.5 to analyse the deal and return structured JSON."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback(brand_tier)
    prompt = _build_user_prompt(
        contract_text=contract_text, deal_title=deal_title, deal_amount=deal_amount,
        brand_name=brand_name, brand_tier=brand_tier,
    )
    try:
        text = await _call_claude(prompt, api_key)
    except Exception as e:
        logger.warning(f"AI analysis failed, using fallback: {e}")
        return _fallback(brand_tier)
    parsed = _parse_json_payload(text or "")
    return parsed or _fallback(brand_tier)


def _fallback(tier: str) -> Dict:
    tier_map = {
        "fortune500": ("verified", 94, [], ["Blue-chip counterparty", "Historical on-time payment"]),
        "enterprise": ("verified", 87, [], ["Established payer", "Strong solvency"]),
        "growth": ("needs_review", 72, ["Moderate payment velocity"], ["Scaling revenue"]),
        "seed": ("needs_review", 58, ["Low cash reserves", "Limited payment history"], ["High-growth potential"]),
    }
    status, conf, red, green = tier_map.get(tier, tier_map["growth"])
    return {
        "verification_status": status,
        "confidence_pct": conf,
        "key_terms": {
            "deliverables": "Sponsored content post + stories",
            "payment_terms_days": 60,
            "exclusivity": "category",
            "ip_rights": "shared",
            "kill_fee": "no",
        },
        "red_flags": red,
        "green_flags": green,
        "underwriter_note": f"Heuristic assessment for {tier}-tier counterparty. AI service unavailable — fallback applied.",
    }
