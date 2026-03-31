import logging
import sys
import json
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (
    LLM_PROVIDER, LLM_MODELS,
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY,
    MAX_TOKENS, TEMPERATURE,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


# -------------------------------
# 🔹 MAIN ENTRY POINT
# -------------------------------

def call_llm(
    user_message: str,
    system_prompt: str = "You are a precise technical analyst. Always return valid JSON only.",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:

    t   = temperature if temperature is not None else TEMPERATURE
    mtk = max_tokens  if max_tokens  is not None else MAX_TOKENS

    provider = LLM_PROVIDER.lower()
    model    = LLM_MODELS.get(provider)

    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(f"[LLM] {provider.upper()} | Attempt {attempt+1}")

            if provider == "openai":
                raw = _call_openai(user_message, system_prompt, model, t, mtk)
            elif provider == "anthropic":
                raw = _call_anthropic(user_message, system_prompt, model, t, mtk)
            elif provider == "gemini":
                raw = _call_gemini(user_message, system_prompt, model, t, mtk)
            else:
                raise RuntimeError(f"Invalid provider: {provider}")

            cleaned = _clean_response(raw)

            # Validate JSON early
            if _is_valid_json(cleaned):
                return cleaned

            logger.warning("Invalid JSON returned, retrying...")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")

        time.sleep(1)

    raise RuntimeError("LLM failed after retries")


# -------------------------------
# 🔹 RESPONSE HANDLING
# -------------------------------

def _clean_response(text: str) -> str:
    """Remove markdown fences and whitespace."""
    text = text.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    return text.strip()


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except:
        return False


# -------------------------------
# 🔹 PROVIDERS
# -------------------------------

def _call_openai(user_msg, system_msg, model, temperature, max_tokens):
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


def _call_anthropic(user_msg, system_msg, model, temperature, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_msg,
        messages=[{"role": "user", "content": user_msg}],
    )

    return response.content[0].text


def _call_gemini(user_msg, system_msg, model, temperature, max_tokens):
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_msg,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )

    response = model.generate_content(user_msg)

    return response.text