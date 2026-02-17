"""Decision skill – uses Agno Agent + OpenAI to produce a final decision."""

import json
import re

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.ai.schemas import (
    ActionType,
    DecisionOut,
    OfferExtraction,
    ShiftValidation,
)
from app.ai.skills.decision.prompt import SYSTEM_PROMPT
from app.common.config import settings


def _build_agent() -> Agent:
    """Create a reusable Agno Agent for decision-making."""
    return Agent(
        name="decision",
        model=OpenAIChat(
            id=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
        ),
        instructions=[SYSTEM_PROMPT],
        output_schema=DecisionOut,
        structured_outputs=True,
        markdown=False,
    )


def _parse_fallback(text: str, validations: list[ShiftValidation]) -> DecisionOut:
    """Fallback: extract JSON from raw text and validate with Pydantic."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        # Ensure validations are carried over
        if "validations" not in data or not data["validations"]:
            data["validations"] = [v.model_dump() for v in validations]
        return DecisionOut.model_validate(data)

    # Absolute fallback
    return DecisionOut(
        action=ActionType.ASK_DETAILS,
        reply_text="Desculpe, não consegui processar. Pode repetir a oferta?",
        validations=validations,
    )


def _build_user_message(
    extraction: OfferExtraction,
    validations: list[ShiftValidation],
) -> str:
    """Compose the user message sent to the decision agent."""
    ext_json = extraction.model_dump_json(indent=2)
    val_json = json.dumps(
        [v.model_dump(mode="json") for v in validations], indent=2, default=str,
    )
    return (
        f"Offer extraction:\n{ext_json}\n\n"
        f"Schedule validations:\n{val_json}"
    )


async def run_decision(
    extraction: OfferExtraction,
    validations: list[ShiftValidation],
) -> DecisionOut:
    """Execute the decision skill.

    Tries structured output first, falls back to manual JSON parsing.
    """
    agent = _build_agent()
    user_msg = _build_user_message(extraction, validations)

    try:
        result = agent.run(user_msg)
        content = result.content

        if isinstance(content, DecisionOut):
            # Ensure validations are attached
            if not content.validations:
                content.validations = validations
            return content

        if isinstance(content, dict):
            if "validations" not in content or not content["validations"]:
                content["validations"] = [v.model_dump() for v in validations]
            return DecisionOut.model_validate(content)

        return _parse_fallback(str(content), validations)

    except Exception:
        try:
            plain_agent = Agent(
                name="decision_fallback",
                model=OpenAIChat(
                    id=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                ),
                instructions=[SYSTEM_PROMPT],
                markdown=False,
            )
            result = plain_agent.run(user_msg)
            return _parse_fallback(str(result.content), validations)
        except Exception:
            return DecisionOut(
                action=ActionType.ASK_DETAILS,
                reply_text="Erro interno. Pode repetir a oferta?",
                validations=validations,
            )
