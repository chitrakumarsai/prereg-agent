"""Vultr Serverless Inference client. The key lives here, in the control plane, and nowhere else."""

import json
import logging
import os
import re
from functools import lru_cache

from openai import OpenAI, OpenAIError

from prereg import config

log = logging.getLogger(__name__)

FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
UNCLOSED_FENCE = re.compile(r"^\s*```[\w-]*\s*$", re.MULTILINE)


class LLMError(RuntimeError):
    """The model could not be reached or did not return something usable."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    key = os.environ.get("VULTR_INFERENCE_KEY", "").strip()
    if not key:
        raise LLMError("VULTR_INFERENCE_KEY is not set")
    return OpenAI(base_url=config.INFERENCE_BASE_URL, api_key=key, timeout=config.LLM_TIMEOUT_S, max_retries=1)


def chat(messages: list[dict], *, max_tokens: int = 3000) -> tuple[str, str]:
    """Return (text, model_used). Falls back to the second model if the first one fails."""
    last_error: Exception | None = None
    for model in (config.MODEL, config.FALLBACK_MODEL):
        try:
            resp = _client().chat.completions.create(
                model=model, messages=messages, temperature=0.1, max_tokens=max_tokens
            )
            text = (resp.choices[0].message.content or "").strip() if resp.choices else ""
            if text:
                return text, model
            last_error = LLMError(f"{model} returned an empty response")
        except OpenAIError as exc:
            log.warning("model %s failed: %s", model, exc)
            last_error = exc
    raise LLMError(f"inference failed on both models: {last_error}")


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply, tolerating code fences and chatter."""
    cleaned = re.sub(r"```(?:json)?", "", text)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("no JSON object in the reply")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"reply is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMError("reply JSON is not an object")
    return data


def extract_code(text: str) -> str:
    """Pull a Python script out of a model reply."""
    blocks = FENCE.findall(text)
    # An unclosed fence (a truncated or sloppy reply) leaves fence lines behind; drop them.
    code = max(blocks, key=len) if blocks else UNCLOSED_FENCE.sub("", text)
    code = code.strip()
    if not code:
        raise LLMError("reply contains no code")
    return code
