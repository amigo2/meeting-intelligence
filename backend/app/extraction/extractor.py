"""Structured extraction: pull decisions + action items from a whole transcript.

Unlike Q&A (which retrieves a few relevant chunks), extraction reads the ENTIRE
transcript in one pass — it must see everything to catch every decision/action item.
The model returns strict JSON so the UI can render cards from it.
"""

import json

from app.core.bedrock import generate

EXTRACT_SYSTEM = (
    "You extract structured intelligence from a meeting transcript. "
    "Return ONLY valid JSON (no markdown fences, no prose) with exactly this shape:\n"
    '{\n'
    '  "summary": "2-3 sentence neutral summary",\n'
    '  "decisions": ["a decision made in the meeting", ...],\n'
    '  "action_items": [{"owner": "name", "task": "what they will do", "due": "when or null"}]\n'
    '}\n'
    "Base everything strictly on the transcript. Use empty lists if there are none. "
    "Do not invent owners, tasks, or dates."
)


def _parse_json(raw: str) -> dict:
    """Parse the model's JSON, tolerating stray markdown fences or wrapping text."""
    text = raw.strip()
    if "{" in text and "}" in text:
        text = text[text.find("{") : text.rfind("}") + 1]
    return json.loads(text)


def extract(transcript_text: str) -> dict:
    """Return {summary, decisions[], action_items[]} for the whole transcript."""
    raw = generate(EXTRACT_SYSTEM, f"Transcript:\n{transcript_text}", max_tokens=1500)
    data = _parse_json(raw)
    # Normalise so the shape is always safe for the UI.
    return {
        "summary": data.get("summary", ""),
        "decisions": data.get("decisions", []),
        "action_items": data.get("action_items", []),
    }
