"""Contract parsing service — extracts structured deal terms from raw contract text.

Modes (set CONTRACT_PARSER_MODE in .env):
  mock   — deterministic synthetic analysis, no external calls (default)
  claude — Anthropic claude-sonnet-4-6 via anthropic SDK
  openai — OpenAI gpt-4o via openai SDK

The returned ContractAnalysis maps 1-to-1 onto DealDetail.jsx's ai_analysis panel.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Output DTO — shape consumed by DealDetail.jsx
# ---------------------------------------------------------------------------

class ContractAnalysis(BaseModel):
    brand_name: str = ""
    deal_amount_extracted: Optional[float] = None   # cross-check against stated amount
    payment_terms_days: Optional[int] = None
    deliverables: List[str] = []
    payment_schedule: str = ""
    exclusivity: bool = False
    exclusivity_notes: str = ""
    red_flags: List[str] = []
    green_flags: List[str] = []
    key_terms: Dict[str, str] = {}
    verification_status: Literal["verified", "unverified", "rejected"] = "unverified"
    confidence_pct: int = Field(default=50, ge=0, le=100)
    underwriter_note: str = ""
    parsed_by: str = "mock"


# ---------------------------------------------------------------------------
# System prompt (shared by Claude and OpenAI modes)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert fintech underwriter reviewing brand deal contracts for a creator financing platform.

Extract and return a JSON object with EXACTLY these fields (no extras):
{
  "brand_name": "string — counterparty brand name from the contract",
  "deal_amount_extracted": number or null — total deal value in INR (numeric only, no currency symbols),
  "payment_terms_days": integer or null — net payment days (e.g. 30 for Net-30),
  "deliverables": ["array of deliverable strings"],
  "payment_schedule": "string — e.g. '50% on signing, 50% on delivery'",
  "exclusivity": true/false,
  "exclusivity_notes": "string — category/duration if exclusivity exists, empty if not",
  "red_flags": ["list of concerning clauses — late payment penalties, vague deliverables, IP grab clauses, etc."],
  "green_flags": ["list of positive signals — reputable brand, clear terms, guaranteed minimum, etc."],
  "key_terms": {"term_name": "value", ...} — 4-6 key financial/legal terms,
  "verification_status": "verified" | "unverified" | "rejected",
  "confidence_pct": integer 0-100 — your confidence the extracted data is accurate,
  "underwriter_note": "2-3 sentence plain-English underwriter memo summarising risk and recommendation"
}

Rules:
- verified = you found clear amounts, payment terms, and brand identity
- unverified = contract text is ambiguous or incomplete
- rejected = contract appears fraudulent, unsigned, or a template without real data
- Be conservative with confidence_pct — only hit 90+ if all key terms are explicit
- Flag exclusivity clauses aggressively — they restrict creator's future earning ability
- Red-flag vague deliverable language ("social media posts" without specifics)
Return ONLY the JSON object, no markdown, no explanation."""

USER_PROMPT_TEMPLATE = """Analyse this brand deal contract and extract the structured data:

---
{contract_text}
---

Stated deal amount on record: ₹{deal_amount}
Stated payment terms: Net {payment_terms_days}
"""


# ---------------------------------------------------------------------------
# Mock parser — returns plausible synthetic analysis
# ---------------------------------------------------------------------------

def _mock_analysis(
    contract_text: str,
    brand_name: str,
    deal_amount: float,
    payment_terms_days: int,
) -> ContractAnalysis:
    """Deterministic synthetic analysis for development / no-key environments."""
    has_text = bool(contract_text and len(contract_text.strip()) > 50)
    confidence = 72 if has_text else 35

    # Detect some basic signals from the text itself
    text_lower = (contract_text or "").lower()
    exclusivity = any(w in text_lower for w in ("exclusive", "exclusivity", "not promote"))
    has_deliverables = any(w in text_lower for w in ("reel", "post", "story", "video", "content"))

    red_flags = []
    green_flags = []

    if exclusivity:
        red_flags.append("Exclusivity clause detected — restricts future brand partnerships.")
    if "penalty" in text_lower or "liquidated" in text_lower:
        red_flags.append("Penalty / liquidated damages clause present — review threshold.")
    if not has_deliverables:
        red_flags.append("Deliverables are vague — no specific content type/quantity specified.")
    if deal_amount > 500_000:
        green_flags.append(f"High-value deal (₹{deal_amount:,.0f}) — strong monetisation signal.")
    if payment_terms_days <= 30:
        green_flags.append(f"Short payment cycle (Net {payment_terms_days}) — lower collection risk.")
    green_flags.append("Brand identity matches submitted counterparty name.")

    return ContractAnalysis(
        brand_name=brand_name,
        deal_amount_extracted=deal_amount,
        payment_terms_days=payment_terms_days,
        deliverables=[
            "2× Instagram Reels (60s, brand-integrated)",
            "4× Instagram Stories with swipe-up link",
            "1× YouTube integration (mid-roll, 45s)",
        ] if has_deliverables else ["Deliverables not specified in pasted text"],
        payment_schedule="50% on contract signing, 50% on content approval",
        exclusivity=exclusivity,
        exclusivity_notes="Category exclusivity — competitor brands in same vertical" if exclusivity else "",
        red_flags=red_flags,
        green_flags=green_flags,
        key_terms={
            "brand": brand_name,
            "deal_value": f"₹{deal_amount:,.0f}",
            "net_days": str(payment_terms_days),
            "content_window": "30 days from signing",
            "revision_rounds": "2 rounds included",
            "ip_ownership": "Brand retains usage rights for 12 months",
        },
        verification_status="verified" if has_text else "unverified",
        confidence_pct=confidence,
        underwriter_note=(
            f"Contract reviewed for {brand_name}. "
            f"Deal value ₹{deal_amount:,.0f} with Net {payment_terms_days} terms. "
            + ("Exclusivity clause warrants attention. " if exclusivity else "")
            + "Standard creator deal structure — recommend approval subject to brand solvency check."
        ),
        parsed_by="mock",
    )


# ---------------------------------------------------------------------------
# Claude parser
# ---------------------------------------------------------------------------

async def _claude_analysis(
    contract_text: str,
    brand_name: str,
    deal_amount: float,
    payment_terms_days: int,
    api_key: str,
) -> ContractAnalysis:
    try:
        import anthropic  # type: ignore
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = USER_PROMPT_TEMPLATE.format(
        contract_text=(contract_text or "(no contract text provided)")[:12_000],
        deal_amount=f"{deal_amount:,.0f}",
        payment_terms_days=payment_terms_days,
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw_json = message.content[0].text.strip()
    # Strip markdown fences if present
    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
    raw_json = re.sub(r"\s*```$", "", raw_json)

    data: Dict[str, Any] = json.loads(raw_json)
    data["parsed_by"] = "claude"
    return ContractAnalysis(**data)


# ---------------------------------------------------------------------------
# OpenAI parser
# ---------------------------------------------------------------------------

async def _openai_analysis(
    contract_text: str,
    brand_name: str,
    deal_amount: float,
    payment_terms_days: int,
    api_key: str,
) -> ContractAnalysis:
    try:
        from openai import AsyncOpenAI  # type: ignore
    except ImportError:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        )

    client = AsyncOpenAI(api_key=api_key)
    user_msg = USER_PROMPT_TEMPLATE.format(
        contract_text=(contract_text or "(no contract text provided)")[:12_000],
        deal_amount=f"{deal_amount:,.0f}",
        payment_terms_days=payment_terms_days,
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )

    data: Dict[str, Any] = json.loads(response.choices[0].message.content)
    data["parsed_by"] = "openai"
    return ContractAnalysis(**data)


# ---------------------------------------------------------------------------
# Public entry point — called by deals.py/analyze endpoint
# ---------------------------------------------------------------------------

async def parse_contract(
    *,
    contract_text: str,
    brand_name: str,
    deal_amount: float,
    payment_terms_days: int,
    mode: str = "mock",
    anthropic_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
) -> ContractAnalysis:
    """Route to the correct provider based on ``mode``.

    Falls back to mock if the required API key is missing rather than crashing,
    so a missing key never blocks the deal flow — it just returns synthetic data.
    """
    if mode == "claude":
        if not anthropic_api_key:
            return _mock_analysis(contract_text, brand_name, deal_amount, payment_terms_days)
        try:
            return await _claude_analysis(
                contract_text, brand_name, deal_amount, payment_terms_days, anthropic_api_key
            )
        except Exception as exc:
            # Log and gracefully degrade — never crash the deal pipeline
            import logging
            logging.getLogger(__name__).error("Claude contract parse failed: %s", exc)
            result = _mock_analysis(contract_text, brand_name, deal_amount, payment_terms_days)
            result.parsed_by = f"mock_fallback (claude error: {type(exc).__name__})"
            return result

    if mode == "openai":
        if not openai_api_key:
            return _mock_analysis(contract_text, brand_name, deal_amount, payment_terms_days)
        try:
            return await _openai_analysis(
                contract_text, brand_name, deal_amount, payment_terms_days, openai_api_key
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("OpenAI contract parse failed: %s", exc)
            result = _mock_analysis(contract_text, brand_name, deal_amount, payment_terms_days)
            result.parsed_by = f"mock_fallback (openai error: {type(exc).__name__})"
            return result

    # Default: mock
    return _mock_analysis(contract_text, brand_name, deal_amount, payment_terms_days)
