"""Pydantic schemas shared across AI skills and API."""

from datetime import date, time
from enum import Enum

from pydantic import BaseModel, Field


# ── Inbound ──────────────────────────────────────────────────────────────────

class MessageIn(BaseModel):
    """Payload received from the WhatsApp webhook (simplified)."""
    phone: str = Field(..., description="Sender phone number (E.164)")
    text: str = Field(..., description="Raw message text")


# ── Offer Extraction ─────────────────────────────────────────────────────────

class ShiftType(str, Enum):
    DIURNO = "diurno"
    NOTURNO = "noturno"


class ShiftCandidate(BaseModel):
    """A single shift parsed from the message."""
    date: date
    shift_type: ShiftType
    start_time: time = Field(default=None, description="Defaults based on shift_type")
    duration_hours: int = Field(default=12)
    location: str | None = None


class OfferExtraction(BaseModel):
    """Output of the offer_extraction skill."""
    is_offer: bool = Field(..., description="True if the message is a shift offer")
    shifts: list[ShiftCandidate] = Field(default_factory=list)
    raw_summary: str | None = None


# ── Schedule Check ────────────────────────────────────────────────────────────

class ShiftValidation(BaseModel):
    """Result of checking one ShiftCandidate against the doctor's schedule."""
    shift: ShiftCandidate
    ok: bool
    reason: str | None = None


# ── Decision ──────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ASK_DETAILS = "ask_details"
    NOT_AN_OFFER = "not_an_offer"


class DecisionOut(BaseModel):
    """Final decision returned by the workflow."""
    action: ActionType
    reply_text: str = Field(..., description="Suggested WhatsApp reply")
    validations: list[ShiftValidation] = Field(default_factory=list)
