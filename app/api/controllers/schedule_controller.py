"""Controllers for schedule management endpoints."""

from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AvailabilityRule, BusySlot, Doctor, RecurringBusyRule
from app.db.session import get_db

router = APIRouter(prefix="/schedule")


# ── Request schemas ──────────────────────────────────────────────────────────

class DoctorIn(BaseModel):
    """Create a doctor (convenience endpoint for testing)."""
    name: str
    phone: str


class AvailabilityIn(BaseModel):
    """Weekly availability window."""
    doctor_id: int
    weekday: int = Field(..., ge=0, le=6, description="0=Mon … 6=Sun")
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")


class BusySlotIn(BaseModel):
    """One-off busy block."""
    doctor_id: int
    start_dt: str = Field(..., description="ISO datetime")
    end_dt: str = Field(..., description="ISO datetime")
    reason: str | None = None


class RecurringBusyIn(BaseModel):
    """Recurring weekly busy block."""
    doctor_id: int
    weekday: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    label: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(value: str) -> time:
    """Parse HH:MM string into a time object."""
    return time.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(value)


async def _get_doctor(db: AsyncSession, doctor_id: int) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/doctor")
async def create_doctor(payload: DoctorIn, db: AsyncSession = Depends(get_db)):
    """Register a doctor (for testing convenience)."""
    doctor = Doctor(name=payload.name, phone=payload.phone)
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)
    return {"id": doctor.id, "name": doctor.name, "phone": doctor.phone}


@router.post("/availability")
async def create_availability(
    payload: AvailabilityIn,
    db: AsyncSession = Depends(get_db),
):
    """Register weekly availability for a doctor."""
    await _get_doctor(db, payload.doctor_id)

    rule = AvailabilityRule(
        doctor_id=payload.doctor_id,
        weekday=payload.weekday,
        start_time=_parse_time(payload.start_time),
        end_time=_parse_time(payload.end_time),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "status": "created"}


@router.post("/busy")
async def create_busy_slot(
    payload: BusySlotIn,
    db: AsyncSession = Depends(get_db),
):
    """Register a one-off busy slot."""
    await _get_doctor(db, payload.doctor_id)

    slot = BusySlot(
        doctor_id=payload.doctor_id,
        start_dt=_parse_datetime(payload.start_dt),
        end_dt=_parse_datetime(payload.end_dt),
        reason=payload.reason,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return {"id": slot.id, "status": "created"}


@router.post("/recurring-busy")
async def create_recurring_busy(
    payload: RecurringBusyIn,
    db: AsyncSession = Depends(get_db),
):
    """Register a recurring weekly busy block (e.g. lunch)."""
    await _get_doctor(db, payload.doctor_id)

    rule = RecurringBusyRule(
        doctor_id=payload.doctor_id,
        weekday=payload.weekday,
        start_time=_parse_time(payload.start_time),
        end_time=_parse_time(payload.end_time),
        label=payload.label,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "status": "created"}
