"""Schedule check skill – deterministic, no LLM.

Delegates to the schedule_tool for each ShiftCandidate.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import ShiftCandidate, ShiftValidation
from app.ai.tools.schedule_tool import check_shift


async def run_schedule_check(
    db: AsyncSession,
    doctor_id: int,
    candidates: list[ShiftCandidate],
) -> list[ShiftValidation]:
    """Validate every candidate shift against the doctor's schedule."""
    results: list[ShiftValidation] = []
    for candidate in candidates:
        validation = await check_shift(db, doctor_id, candidate)
        results.append(validation)
    return results
