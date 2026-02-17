"""Placeholder for WhatsApp Cloud API integration.

TODO: Implement actual WhatsApp message sending when ready.
"""


async def send_message(to: str, text: str) -> dict:
    """Send a WhatsApp message to the given phone number.

    Args:
        to: Recipient phone in E.164 format.
        text: Message body.

    Returns:
        API response dict (stubbed for now).
    """
    # TODO: Integrate with WhatsApp Cloud API
    return {"status": "not_implemented", "to": to, "text": text}
