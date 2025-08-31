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

    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    lines = [ln.strip().lstrip("•-").strip() for ln in r.output_text.splitlines() if ln.strip()]
    uniq = []
    for q in lines:
        if q and q not in uniq:
            uniq.append(q)
    if not uniq:
        raise RuntimeError("Empty questions from model.")
    return uniq[:n]

def analyze_session(job_title: str, qa_pairs: list[dict]) -> dict:
    """
    Analyze per-answer + overall.
    qa_pairs: [{"order":1,"question":"...","answer":"..."}, ...]
    Returns:
    {
      "answers": [
        {"order":1,"strengths":"..","weaknesses":"..","score":3},
        ...
      ],
      "session": {
        "strengths":"..","weaknesses":"..","recommendation":"..","overall_score":3.8
      }
    }
    """
    _require_client()

    # Build a compact prompt; ask STRICT JSON only.
    prompt = (
        "أنت مدرّب مقابلات. حلّل إجابات عربية لمقابلة وفق الآتي:\n"
        "1) لكل سؤال: strengths, weaknesses, score (عدد صحيح من 1 إلى 5).\n"
        "2) ملخص عام: strengths, weaknesses, recommendation, overall_score (متوسط من 1 إلى 5، رقم عشري بمرتبة واحدة).\n"
        "أعد JSON فقط بهذه البنية دون أي نص خارجي:\n"
        "{\n"
        '  "answers":[{"order":1,"strengths":"..","weaknesses":"..","score":3},...],\n'
        '  "session":{"strengths":"..","weaknesses":"..","recommendation":"..","overall_score":3.8}\n'
        "}\n\n"
        f"المسمى الوظيفي: {job_title}\n"
        "الأسئلة والإجابات:\n"
    )
    for item in qa_pairs:
        prompt += f"- س{item['order']}: {item['question']}\n  إجابة: {item.get('answer','')}\n"

    try:
        r = _client.responses.create(model="gpt-4o-mini", input=prompt)
        txt = r.output_text.strip()
        m = re.search(r"\{.*\}", txt, flags=re.S)
        data = json.loads(m.group(0) if m else txt)

        # Defensive normalization
        answers = data.get("answers", []) or []
        session = data.get("session", {}) or {}
        for a in answers:
            a["order"] = int(a.get("order", 0) or 0)
            s = a.get("score")
            a["score"] = int(s) if isinstance(s, (int, float, str)) and str(s).isdigit() else None
            a["strengths"] = (a.get("strengths") or "").strip()
            a["weaknesses"] = (a.get("weaknesses") or "").strip()

        # If model didn't return overall_score, compute mean of available scores
        if "overall_score" not in session or session.get("overall_score") in (None, ""):
            valid = [a["score"] for a in answers if isinstance(a["score"], int)]
            session["overall_score"] = round(sum(valid) / len(valid), 1) if valid else None

        session["strengths"] = (session.get("strengths") or "").strip()
        session["weaknesses"] = (session.get("weaknesses") or "").strip()
        session["recommendation"] = (session.get("recommendation") or "").strip()

        return {"answers": answers, "session": session}

    except openai_error.RateLimitError:
        # If quota is exceeded, return neutral structure (avoid crashing)
        return {"answers": [
                    {"order": item["order"], "strengths": "", "weaknesses": "", "score": None}
                    for item in qa_pairs
                ],
                "session": {"strengths": "", "weaknesses": "", "recommendation": "", "overall_score": None}}

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