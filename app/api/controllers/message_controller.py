"""Controller for the /message endpoint (AI motor)."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ActionType, DecisionOut, MessageIn, ShiftType
from app.ai.workflows.shift_offer_workflow import shift_offer_workflow
from app.db.models import BusySlot, Doctor
from app.db.session import get_db

router = APIRouter()

# Default start times (same as schedule_tool)
_SHIFT_DEFAULTS = {
    ShiftType.DIURNO: datetime.min.time().replace(hour=7),
    ShiftType.NOTURNO: datetime.min.time().replace(hour=19),
}


@router.post("/message", response_model=DecisionOut)
async def process_message(
    payload: MessageIn,
    db: AsyncSession = Depends(get_db),
) -> DecisionOut:
    """Receive a WhatsApp message and return action + suggested reply.

    The endpoint does NOT send the reply automatically.
    When the decision is 'accept', a BusySlot is created so the
    same time slot won't be accepted twice.
    """
    # Find doctor by phone
    result = await db.execute(
        select(Doctor).where(Doctor.phone == payload.phone)
    )
    doctor = result.scalars().first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    decision = await shift_offer_workflow(db, doctor.id, payload.text)

    # Auto-create BusySlot for accepted shifts to avoid double-booking
    if decision.action == ActionType.ACCEPT:
        for v in decision.validations:
            if not v.ok:
                continue
            shift = v.shift
            start_time = shift.start_time or _SHIFT_DEFAULTS.get(shift.shift_type)
            # Strip timezone if present
            if start_time and start_time.tzinfo:
                start_time = start_time.replace(tzinfo=None)

            start_dt = datetime.combine(shift.date, start_time)
            end_dt = start_dt + timedelta(hours=shift.duration_hours)

            busy = BusySlot(
                doctor_id=doctor.id,
                start_dt=start_dt,
                end_dt=end_dt,
                reason=f"Plantão aceito – {shift.location or 'sem local'}",
            )

            db.add(busy)

        await db.commit()

    return decision
