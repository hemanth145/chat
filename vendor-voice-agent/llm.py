import json

import anthropic

from config import ANTHROPIC_API_KEY, BUSINESS_INFO, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ESCALATE_TOOL = {
    "name": "escalate_to_human",
    "description": (
        "Call this when the vendor's request is something you should not handle yourself: "
        "pricing negotiation, a dispute or complaint, anything outside the business basics "
        "you were given, or when the vendor explicitly asks for a real person. "
        "Do not call this for routine questions you can answer from the business info provided."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Short reason for the handoff, written for the business owner to read.",
            }
        },
        "required": ["reason"],
    },
}


def build_system_prompt(vendor_name: str | None, history_summaries: list[str]) -> str:
    known_vendor = (
        f"This caller has called before. Their name on file is: {vendor_name or 'unknown, ask for it if natural'}."
        if history_summaries
        else "This is the first recorded call from this phone number."
    )
    history_block = (
        "\n".join(f"- {s}" for s in history_summaries) if history_summaries else "(none)"
    )
    return f"""You are a phone assistant answering vendor calls on behalf of the business owner.
You are speaking out loud on a phone call — keep replies short, natural, and conversational.
Never use markdown, bullet points, or anything that isn't speakable.

{known_vendor}

Summaries of recent past calls with this vendor:
{history_block}

Business basics you can answer from directly:
{BUSINESS_INFO}

Rules:
- Answer routine questions about the basics above directly and confidently.
- If you don't know something and it isn't a basic question, say you'll have the owner follow up — don't guess.
- If the topic needs the owner (pricing negotiation, a dispute, anything explicitly listed as
  needing escalation, or the vendor asks for a real person), call the escalate_to_human tool.
- Keep the conversation moving towards a natural close once the vendor's question is answered.
"""


def get_reply(system_prompt: str, conversation: list[dict]) -> tuple[str, bool, str | None]:
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=system_prompt,
        messages=conversation,
        tools=[ESCALATE_TOOL],
    )

    text_parts = []
    escalate = False
    reason = None
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use" and block.name == "escalate_to_human":
            escalate = True
            reason = block.input.get("reason", "Vendor asked for a real person.")

    reply = " ".join(part.strip() for part in text_parts).strip()
    if not reply:
        reply = "Let me connect you with someone who can help with that."
    return reply, escalate, reason


SUMMARY_SYSTEM_PROMPT = """You summarize a phone call transcript between an AI assistant and a vendor,
for the business owner who was not on the call. Reply with ONLY a JSON object, no other text, in this
exact shape: {"summary": "1-3 sentence summary", "important": true or false}.
Mark "important" true if the owner should personally follow up (a problem, a decision needed,
an escalation, anything time-sensitive or unusual). Otherwise false for routine calls."""


def summarize_call(transcript_text: str) -> tuple[str, bool]:
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=SUMMARY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript_text}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    try:
        data = json.loads(raw)
        return data.get("summary", raw), bool(data.get("important", False))
    except json.JSONDecodeError:
        return raw, False
