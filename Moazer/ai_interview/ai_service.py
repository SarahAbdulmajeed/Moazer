"""
OpenAI-only adapter:
- No fallback questions anymore.
- If OPENAI_API_KEY is missing or the call fails, we raise a clear error.

Usage from views:
- generate_questions(job_title, n=5) -> list[str]
- analyze_answers(job_title, answers_text) -> dict[str, str]
"""

import os
import json
import re

from django.core.exceptions import ImproperlyConfigured

# Read API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

try:
    from openai import OpenAI  # pip install openai>=1.0
except Exception as e:
    raise ImproperlyConfigured(
        "OpenAI SDK is not installed. Run: pip install --upgrade openai"
    ) from e

# Create client (will fail later if key missing)
_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def _require_client():
    """
    Ensure client and key exist; raise clear error if not configured.
    """
    if not _client:
        raise ImproperlyConfigured(
            "OPENAI_API_KEY is missing. Set it as an environment variable before running the server."
        )


def _openai_generate_questions(job_title: str, n: int = 5) -> list[str]:
    """
    Ask OpenAI to generate n Arabic interview questions for the given job title.
    Returns a Python list of strings.
    """
    prompt = (
        f"اكتب {n} أسئلة مقابلة عمل باللغة العربية لمسمى وظيفي: {job_title}.\n"
        "اجعلها واضحة ومهنية ومناسبة للمبتدئ.\n"
        "أعطني فقط قائمة الأسئلة، كل سؤال في سطر مستقل، بدون أرقام وبدون شرح."
    )

    # Using the Responses API as في التوثيق الحديث
    resp = _client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )
    content = resp.output_text.strip()

    # Split per line, strip bullet chars
    lines = [ln.strip().lstrip("•-").strip() for ln in content.splitlines() if ln.strip()]
    # Filter empty / duplicates defensively
    uniq = []
    for q in lines:
        if q and q not in uniq:
            uniq.append(q)
    if not uniq:
        # If the model returned something odd
        raise RuntimeError("OpenAI returned empty questions. Try again or check your prompt/quota.")
    return uniq[:n]


def _openai_analyze(job_title: str, answers_text: str) -> dict:
    """
    Ask OpenAI to summarize strengths/weaknesses/recommendation in Arabic and return a dict.
    """
    prompt = (
        "حلّل إجابات مقابلة عمل عربية بشكل موجز. أعطني JSON بالمفاتيح العربية التالية فقط:\n"
        "strengths, weaknesses, recommendation\n"
        "بدون أي نص خارج JSON.\n\n"
        f"الدور/المسمى: {job_title}\n"
        f"الإجابات:\n{answers_text}\n"
    )
    resp = _client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )
    txt = resp.output_text.strip()

    # Extract JSON strictly
    m = re.search(r"\{.*\}", txt, flags=re.S)
    if not m:
        raise RuntimeError("OpenAI did not return JSON as requested.")
    obj = json.loads(m.group(0))
    return {
        "strengths": obj.get("strengths", ""),
        "weaknesses": obj.get("weaknesses", ""),
        "recommendation": obj.get("recommendation", ""),
    }


# ---------- PUBLIC API ----------

def generate_questions(job_title: str, n: int = 5) -> list[str]:
    """
    OpenAI-only generator. Raises ImproperlyConfigured if key is missing.
    """
    _require_client()
    return _openai_generate_questions(job_title, n)


def analyze_answers(job_title: str, answers_text: str) -> dict:
    """
    OpenAI-only analyzer. Raises ImproperlyConfigured if key is missing.
    """
    _require_client()
    return _openai_analyze(job_title, answers_text)