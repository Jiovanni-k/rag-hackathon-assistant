"""Gemini client with model fallback.

When a model is overloaded (503/429) or retired (404) it is skipped for LLM_COOLDOWN_S seconds,
so later calls go straight to a working model instead of waiting for the same failure again.
"""
import json
import os
import time
from functools import lru_cache

from google import genai
from google.genai import errors, types

from rag import config

FALLBACK_CODES = (404, 429, 500, 503, 504)
_cooldown = {}   # model -> time it may be tried again


class LLMUnavailable(Exception):
    pass


@lru_cache(maxsize=1)
def _client():
    return genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options=types.HttpOptions(timeout=config.LLM_TIMEOUT_MS,
                                       retry_options=types.HttpRetryOptions(attempts=1)),
    )


def _models(preferred):
    models = list(dict.fromkeys(preferred))
    now = time.time()
    ready = [m for m in models if _cooldown.get(m, 0) <= now]
    return ready or models                                   # all cooling down: try anyway


def generate(prompt, json_output=False, temperature=0.1, fast=False):
    """fast=True uses the small models (for short classification/translation calls)."""
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json" if json_output else "text/plain",
    )
    last = None
    for model in _models(config.LLM_FAST_MODELS if fast else config.LLM_MODELS):
        try:
            response = _client().models.generate_content(model=model, contents=prompt, config=cfg)
            text = response.text or ""
            return json.loads(text) if json_output else text
        except errors.APIError as e:
            if e.code not in FALLBACK_CODES:
                raise                                    # e.g. invalid API key: don't hide it
            _cooldown[model] = time.time() + config.LLM_COOLDOWN_S
            last = e
        except json.JSONDecodeError as e:
            last = e
        except Exception as e:                           # timeouts / network errors
            _cooldown[model] = time.time() + config.LLM_COOLDOWN_S
            last = e
    raise LLMUnavailable(str(last))
