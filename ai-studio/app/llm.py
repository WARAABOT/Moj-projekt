"""Poziv Claudea koji vraća provjereni Pydantic objekt."""
import anthropic
from pydantic import BaseModel

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


class LLMError(Exception):
    pass


def ask[T: BaseModel](system: str, prompt: str, schema: type[T], effort: str = "low") -> T:
    if _client is None:
        raise LLMError("ANTHROPIC_API_KEY nije postavljen")
    # fallbacks="default": ako model odbije zahtjev, API ga sam ponovi na drugom modelu
    resp = _client.beta.messages.parse(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise LLMError("Model je odbio zahtjev")
    if resp.parsed_output is None:
        raise LLMError(f"Nije stigao ispravan odgovor (stop_reason={resp.stop_reason})")
    return resp.parsed_output
