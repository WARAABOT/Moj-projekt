"""Writes the video script (title, scenes, metadata) with Claude."""
import json

import anthropic

MODEL = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]  # retry on another model if a request is declined

FORMATS = {
    "short": "A YouTube Short of 40-55 seconds (110-140 words total). First sentence is a hook "
             "that makes people stop scrolling. 5-8 scenes. End with a punchy line, no 'subscribe' begging.",
    "long": "A 8-10 minute YouTube video (1300-1600 words total). Strong hook in the first 15 seconds, "
            "then a clear structure with mini cliffhangers. 30-40 scenes. End with a short recap "
            "and one natural call to subscribe.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "3-8 word topic label, used to avoid repeats"},
        "title": {"type": "string", "description": "Under 70 characters, curiosity-driven, not clickbait lies"},
        "description": {"type": "string", "description": "150-300 words, first 2 lines hook, then summary"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "thumbnail_text": {"type": "string", "description": "2-4 punchy words for the thumbnail"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "narration": {"type": "string", "description": "What the voice says in this scene"},
                    "footage_query": {"type": "string", "description": "2-4 word generic stock-footage "
                                      "search, e.g. 'ancient ruins fog'. No brand, game or person names."},
                },
                "required": ["narration", "footage_query"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["topic", "title", "description", "tags", "thumbnail_text", "scenes"],
    "additionalProperties": False,
}


def _create(client, **kw):
    r = client.beta.messages.create(model=MODEL, max_tokens=16000, betas=BETAS, fallbacks="default", **kw)
    if r.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined: {r.stop_details}")
    return r


def research(client, brief: str) -> str:
    """Searches the web and returns dated news notes with sources."""
    messages = [{"role": "user", "content":
                 f"Channel focus:\n{brief}\n\nSearch the web for the most important news and facts "
                 "from the last 7 days on this topic. Return concise bullet notes, each with its date, "
                 "source name and whether it is official or a rumor."}]
    for _ in range(5):  # web search may pause a long turn; continue it
        r = _create(client, messages=messages, output_config={"effort": "low"},
                    tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 6}])
        if r.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": r.content})
    return "\n".join(b.text for b in r.content if b.type == "text")


def write_script(channel: dict, fmt: str, past_topics: list[str], today: str) -> dict:
    client = anthropic.Anthropic()
    notes = research(client, channel["brief"]) if channel.get("research") else ""
    prompt = (
        f"You write scripts for the faceless YouTube channel \"{channel['name']}\". Today is {today}.\n"
        f"Channel brief:\n{channel['brief']}\n"
        f"Format: {FORMATS[fmt]}\n\n"
        "Rules: be accurate and specific; never invent facts, numbers or quotes. Each video must teach "
        "or tell something genuinely worth watching, not filler. Write for the ear: short sentences, "
        "no stage directions, no emojis, no markdown in narration.\n"
        f"Topics already covered (pick something clearly different):\n{json.dumps(past_topics[-80:])}\n"
    )
    if notes:
        prompt += f"\nResearch notes (only use facts from here for anything recent):\n{notes}\n"
    r = _create(client, messages=[{"role": "user", "content": prompt}],
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}})
    return json.loads(next(b.text for b in r.content if b.type == "text"))
