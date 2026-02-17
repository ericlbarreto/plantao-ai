"""Controller for the /message endpoint (AI motor)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import DecisionOut, MessageIn
from app.ai.workflows.shift_offer_workflow import shift_offer_workflow
from app.db.models import Doctor
from app.db.session import get_db

router = APIRouter()


@router.post("/message", response_model=DecisionOut)
async def process_message(
    payload: MessageIn,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    """Receive a WhatsApp message and return action + suggested reply.

    The endpoint does NOT send the reply automatically.
    """
    # Find doctor by phone
    result = await db.execute(
        select(Doctor).where(Doctor.phone == payload.phone)
    )
    doctor = result.scalars().first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    decision = await shift_offer_workflow(db, doctor.id, payload.text)
    return decision
