"""Offer extraction skill – uses Agno Agent + OpenAI to parse shift offers."""

import json
import re
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.ai.schemas import OfferExtraction
from app.ai.skills.offer_extraction.prompt import get_system_prompt
from app.common.config import settings


def _build_agent() -> Agent:
    """Create a reusable Agno Agent for offer extraction."""
    return Agent(
        name="offer_extraction",
        model=OpenAIChat(
            id=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
        ),
        instructions=[get_system_prompt()],
        output_schema=OfferExtraction,
        structured_outputs=True,
        markdown=False,
    )


def _parse_fallback(text: str) -> OfferExtraction:
    """Fallback: extract JSON from raw text and validate with Pydantic."""
    # Try to find a JSON block in the response
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        data = json.loads(match.group())
        return OfferExtraction.model_validate(data)
    # Nothing found → not an offer
    return OfferExtraction(is_offer=False, shifts=[], raw_summary=None)


async def run_offer_extraction(message_text: str) -> OfferExtraction:
    """Execute the offer extraction skill.

    Tries structured output via Agno Agent first.
    Falls back to manual JSON parsing if needed.
    """
    agent = _build_agent()

    try:
        result = agent.run(message_text)
        content = result.content

        # If Agent returned a parsed Pydantic model directly
        if isinstance(content, OfferExtraction):
            return content

        # If it returned a dict (some versions do this)
        if isinstance(content, dict):
            return OfferExtraction.model_validate(content)

        # Otherwise treat as string and parse
        return _parse_fallback(str(content))

    except Exception:
        # Last resort: try without output_schema
        try:
            plain_agent = Agent(
                name="offer_extraction_fallback",
                model=OpenAIChat(
                    id=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                ),
                instructions=[get_system_prompt()],
                markdown=False,
            )
            result = plain_agent.run(message_text)
            return _parse_fallback(str(result.content))
        except Exception:
            return OfferExtraction(is_offer=False, shifts=[], raw_summary=None)
