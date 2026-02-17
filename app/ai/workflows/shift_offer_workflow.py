"""Shift-offer workflow – chains the 3 skills in sequence.

Flow:
  1. offer_extraction  (LLM)  → OfferExtraction
  2. schedule_check    (det.) → list[ShiftValidation]
  3. decision          (LLM)  → DecisionOut
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ActionType, DecisionOut, OfferExtraction
from app.ai.skills.decision.skill import run_decision
from app.ai.skills.offer_extraction.skill import run_offer_extraction
from app.ai.skills.schedule_check.skill import run_schedule_check


async def shift_offer_workflow(
    db: AsyncSession,
    doctor_id: int,
    message_text: str,
) -> DecisionOut:
    """Run the full shift-offer pipeline.

    Args:
        db: Async database session.
        doctor_id: ID of the doctor whose schedule to check.
        message_text: Raw WhatsApp message.

    Returns:
        DecisionOut with action + suggested reply_text.
    """

    # ── Step 1: Extract offer from message ───────────────────────────
    extraction: OfferExtraction = await run_offer_extraction(message_text)

    if not extraction.is_offer:
        return DecisionOut(
            action=ActionType.NOT_AN_OFFER,
            reply_text="Não identifiquei uma oferta de plantão na mensagem.",
            validations=[],
        )

    if not extraction.shifts:
        return DecisionOut(
            action=ActionType.ASK_DETAILS,
            reply_text=(
                "Parece uma oferta de plantão, mas não consegui extrair "
                "data ou tipo. Pode enviar mais detalhes?"
            ),
            validations=[],
        )

    # ── Step 2: Check schedule (deterministic) ───────────────────────
    validations = await run_schedule_check(db, doctor_id, extraction.shifts)

    # ── Step 3: Decision (LLM) ───────────────────────────────────────
    decision = await run_decision(extraction, validations)

    return decision
