"""Deterministic schedule checker – no LLM involved."""

from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ShiftCandidate, ShiftType, ShiftValidation
from app.db.models import AvailabilityRule, BusySlot, RecurringBusyRule


# Default start times per shift type
_SHIFT_DEFAULTS: dict[ShiftType, time] = {
    ShiftType.DIURNO: time(7, 0),
    ShiftType.NOTURNO: time(19, 0),
}


def _to_naive(t: time) -> time:
    """Strip timezone info so all comparisons use naive times."""
    if t.tzinfo is not None:
        return t.replace(tzinfo=None)
    return t


def _resolve_start(candidate: ShiftCandidate) -> time:
    """Return explicit start_time or the default for the shift type (always naive)."""
    if candidate.start_time is not None:
        return _to_naive(candidate.start_time)
    return _SHIFT_DEFAULTS[candidate.shift_type]


async def check_shift(
    db: AsyncSession,
    doctor_id: int,
    candidate: ShiftCandidate,
) -> ShiftValidation:
    """Check a single ShiftCandidate against the doctor's schedule.

    Rules applied (in order):
    1. Night shifts crossing midnight → reject with review note.
    2. Must fall inside at least one AvailabilityRule window.
    3. Must not overlap any BusySlot.
    4. Must not overlap any RecurringBusyRule.
    """
    start_time = _resolve_start(candidate)
    duration = timedelta(hours=candidate.duration_hours)
    shift_start_dt = datetime.combine(candidate.date, start_time)
    shift_end_dt = shift_start_dt + duration

    # Rule 1: night shift crossing midnight
    if candidate.shift_type == ShiftType.NOTURNO and shift_end_dt.date() != candidate.date:
        return ShiftValidation(
            shift=candidate,
            ok=False,
            reason="shift crosses midnight (needs review)",
        )

    weekday = candidate.date.weekday()  # 0=Mon … 6=Sun

    # Rule 2: availability window
    avail_rows = (
        await db.execute(
            select(AvailabilityRule).where(
                AvailabilityRule.doctor_id == doctor_id,
                AvailabilityRule.weekday == weekday,
            )
        )
    ).scalars().all()

    if not avail_rows:
        return ShiftValidation(
            shift=candidate, ok=False, reason="no availability rule for this weekday"
        )

    covered = any(
        r.start_time <= start_time and r.end_time >= shift_end_dt.time()
        for r in avail_rows
    )
    if not covered:
        return ShiftValidation(
            shift=candidate, ok=False, reason="shift outside availability window"
        )

    # Rule 3: one-off busy slots
    busy_rows = (
        await db.execute(
            select(BusySlot).where(
                BusySlot.doctor_id == doctor_id,
                BusySlot.start_dt < shift_end_dt,
                BusySlot.end_dt > shift_start_dt,
            )
        )
    ).scalars().all()

    if busy_rows:
        return ShiftValidation(
            shift=candidate,
            ok=False,
            reason=f"conflicts with busy slot: {busy_rows[0].reason or 'busy'}",
        )

    # Rule 4: recurring busy rules
    rec_rows = (
        await db.execute(
            select(RecurringBusyRule).where(
                RecurringBusyRule.doctor_id == doctor_id,
                RecurringBusyRule.weekday == weekday,
            )
        )
    ).scalars().all()

    for rule in rec_rows:
        # Check time overlap
        if rule.start_time < shift_end_dt.time() and rule.end_time > start_time:
            return ShiftValidation(
                shift=candidate,
                ok=False,
                reason=f"conflicts with recurring block: {rule.label or 'recurring busy'}",
            )

    return ShiftValidation(shift=candidate, ok=True)
