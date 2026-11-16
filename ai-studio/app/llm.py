"""AI mozak: prvo besplatni modeli, a tvoja Claude pretplata tek kad zatreba (uz dnevni limit).

Redoslijed se mijenja u .env (LLM_ORDER). Svaki pružatelj koji nema ključ se preskače.
- gemini, groq, openrouter: besplatni API ključevi (OpenAI-kompatibilni)
- claude_code: tvoja Claude pretplata preko Claude Code CLI-ja (`claude -p`)
- claude_api: plaćeni Claude API (samo ako upišeš ANTHROPIC_API_KEY)
"""
import json
import subprocess
import tempfile
import time
from datetime import date

import httpx
from pydantic import BaseModel, ValidationError

from . import db
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, env, flag

ORDER = [p.strip() for p in env("LLM_ORDER", "gemini,groq,openrouter,claude_code,claude_api").split(",") if p.strip()]
# za važne poslove (scenarij dugog videa) prvo probaj Claude, jer je kvaliteta najbitnija
CLAUDE_FOR_IMPORTANT = flag("CLAUDE_FOR_IMPORTANT", True)
CLAUDE_CODE_DAILY_LIMIT = int(env("CLAUDE_CODE_DAILY_LIMIT", "6"))
CLAUDE_CODE_MODEL = env("CLAUDE_CODE_MODEL", "sonnet")

OPENAI_COMPAT = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
               "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash"),
    "groq": ("https://api.groq.com/openai/v1/chat/completions",
             "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions",
                   "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"),
}


class LLMError(Exception):
    pass


def available() -> list[str]:
    out = []
    for p in ORDER:
        if p in OPENAI_COMPAT and env(OPENAI_COMPAT[p][1]):
            out.append(p)
        elif p == "claude_code" and (env("CLAUDE_CODE_OAUTH_TOKEN") or flag("CLAUDE_CODE_LOGGED_IN")):
            out.append(p)
        elif p == "claude_api" and ANTHROPIC_API_KEY:
            out.append(p)
    return out


def _json_instructions(schema: type[BaseModel]) -> str:
    return ("\n\nRespond with ONLY one JSON object (no markdown, no comments) that matches this JSON schema:\n"
            + json.dumps(schema.model_json_schema()))


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise LLMError("Odgovor nema JSON")
    return text[start:end + 1]


def _openai_compat(name: str, system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
    url, key_var, model_var, default_model = OPENAI_COMPAT[name]
    body = {
        "model": env(model_var, default_model),
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt + _json_instructions(schema)}],
        "temperature": 0.8,
    }
    if name != "openrouter":  # neki besplatni modeli na OpenRouteru ne podržavaju JSON način
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(url, headers={"Authorization": f"Bearer {env(key_var)}"}, json=body, timeout=300)
    if r.status_code == 429:
        raise LLMError(f"{name}: potrošen besplatni limit")
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"] or ""
    return schema.model_validate_json(_extract_json(text))


def _claude_code_used_today() -> int:
    return int(db.kv_get(f"claude_code_calls_{date.today()}", "0"))


def _claude_code(system: str, prompt: str, schema: type[BaseModel]) -> BaseModel:
    used = _claude_code_used_today()
    if used >= CLAUDE_CODE_DAILY_LIMIT:
        raise LLMError(f"claude_code: dnevni limit ({CLAUDE_CODE_DAILY_LIMIT}) potrošen")
    db.kv_set(f"claude_code_calls_{date.today()}", str(used + 1))
    # prazna privremena mapa: Claude Code ne učitava nikakav projekt, samo odgovara
    with tempfile.TemporaryDirectory() as cwd:
        p = subprocess.run(
            ["claude", "-p", prompt + _json_instructions(schema),
             "--append-system-prompt", system, "--model", CLAUDE_CODE_MODEL,
             "--output-format", "json", "--json-schema", json.dumps(schema.model_json_schema()),
             "--tools", ""],  # bez alata: samo piše odgovor
            cwd=cwd, capture_output=True, text=True, timeout=900,
        )
    if p.returncode != 0:
        raise LLMError(f"claude_code: {(p.stderr or p.stdout)[-300:]}")
    out = json.loads(p.stdout)
    if out.get("is_error"):
        raise LLMError(f"claude_code: {out.get('result', '')[:300]}")
    if out.get("structured_output"):
        return schema.model_validate(out["structured_output"])
    return schema.model_validate_json(_extract_json(out.get("result", "")))


def _claude_api(system: str, prompt: str, schema: type[BaseModel], effort: str) -> BaseModel:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    # fallbacks="default": ako model odbije zahtjev, API ga sam ponovi na drugom modelu
    resp = client.beta.messages.parse(
        model=CLAUDE_MODEL, max_tokens=16000, system=system,
        messages=[{"role": "user", "content": prompt}],
        output_format=schema, output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise LLMError(f"claude_api: nema odgovora ({resp.stop_reason})")
    return resp.parsed_output


def ask[T: BaseModel](system: str, prompt: str, schema: type[T], effort: str = "low",
                      important: bool = False) -> T:
    order = available()
    if important and CLAUDE_FOR_IMPORTANT:
        order = sorted(order, key=lambda p: not p.startswith("claude"))
    if not order:
        raise LLMError("Nijedan AI nije postavljen: upiši barem GEMINI_API_KEY u .env")
    errors = []
    for name in order:
        try:
            t = time.time()
            if name in OPENAI_COMPAT:
                result = _openai_compat(name, system, prompt, schema)
            elif name == "claude_code":
                result = _claude_code(system, prompt, schema)
            else:
                result = _claude_api(system, prompt, schema, effort)
            db.insert("events", ts=time.time(), agent="AI", message=f"{name} odgovorio za {time.time() - t:.0f} s")
            return result
        except (LLMError, ValidationError, httpx.HTTPError, ValueError, KeyError,
                subprocess.TimeoutExpired, FileNotFoundError) as e:
            errors.append(f"{name}: {str(e)[:150]}")
    raise LLMError(" | ".join(errors))
