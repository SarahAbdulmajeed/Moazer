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

# Phrases that mean "I don't know" / non-answers (add more as needed)
_INVALID_PHRASES = {
     "مامرت علي", "لا ادري", "ما اعرف", "ما أعرف", "ماني عارف", "مدري", "لا اعلم", "لا أعلم",
    "i don't know", "idk", "unknown", "n/a"
}

def _is_invalid_answer(text: str) -> bool:
    """
    Returns True if the answer should NOT be graded:
    - empty/whitespace
    - just dashes or punctuation
    - common 'I don't know' phrases (Arabic & English)
    - very short or gibberish-like (e.g., < = 2 words or mostly symbols/emoji)
    """
    if not text:
        return True
    t = text.strip().lower()
    if not t:
        return True
    # Just a dash or punctuation
    if re.fullmatch(r"[-–—_\.]+", t):
        return True
    # Common 'I don't know' phrases
    norm = re.sub(r"\s+", " ", t)
    if norm in _INVALID_PHRASES:
        return True
    # Too short / likely gibberish (e.g., ≤ 2 tokens, no Arabic letters)
    tokens = re.findall(r"\w+", t, flags=re.UNICODE)
    if len(tokens) <= 2:
        # if it has no Arabic letters at all or looks random
        if not re.search(r"[ء-ي]", t):
            return True
    # Mostly non-letters? (heuristic)
    letters = re.findall(r"[A-Za-zء-ي]", t)
    if letters and (len(letters) / max(1, len(t))) < 0.2:
        return True
    return False

def analyze_session(job_title: str, qa_pairs: list[dict]) -> dict:
    """
    Analyze per-answer + overall with strict handling for invalid answers.
    Any invalid answer gets score=0 and empty strengths/weaknesses,
    and is EXCLUDED from the overall average.
    """
    _require_client()

    # --- Build prompt with strict rules for invalid answers ---
    prompt = (
        "أنت مدرّب مقابلات. حلّل إجابات عربية وفق القواعد التالية:\n"
        "- إذا كانت الإجابة غير صالحة (فارغة، شرطة فقط، «ما أعرف/مدري»، أو عشوائية/غير مرتبطة)، "
        "فضع score=0 واترك strengths و weaknesses فارغتين.\n"
        "- الإجابة الصالحة فقط تُقيّم من 1 إلى 5 (عدد صحيح).\n"
        "- لا تذكر أي تعليقات خارج JSON.\n"
        "- في الملخص العام overall_score احسب المتوسط على الإجابات الصالحة فقط (المستبعدة ذات score=0 لا تُحسب).\n"
        "أعد JSON فقط بهذه البنية:\n"
        "{\n"
        '  "answers":[{"order":1,"strengths":"", "weaknesses":"", "score":0}, ...],\n'
        '  "session":{"strengths":"..","weaknesses":"..","recommendation":"..","overall_score":3.8}\n'
        "}\n\n"
        f"المسمى الوظيفي: {job_title}\n"
        "الأسئلة والإجابات:\n"
    )
    for item in qa_pairs:
        prompt += f"- س{item['order']}: {item['question']}\n  إجابة: {item.get('answer','')}\n"

    # --- Call the model ---
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    txt = r.output_text.strip()
    m = re.search(r"\{.*\}", txt, flags=re.S)
    data = json.loads(m.group(0) if m else txt)

    # --- Normalize model output ---
    answers = data.get("answers", []) or []
    session = data.get("session", {}) or {}

    # Map answers by order for easy overwrite with local validator
    by_order = {a.get("order"): a for a in answers}

    valid_scores = []
    for item in qa_pairs:
        order = int(item.get("order", 0) or 0)
        ans_text = (item.get("answer") or "").strip()
        row = by_order.get(order, {"order": order})

        # Normalize fields coming from model
        row["order"] = order
        row["strengths"] = (row.get("strengths") or "").strip()
        row["weaknesses"] = (row.get("weaknesses") or "").strip()
        s = row.get("score")
        try:
            row["score"] = int(s)
        except Exception:
            row["score"] = None

        # --- Local hard rule: overwrite invalid answers ---
        if _is_invalid_answer(ans_text):
            row["strengths"] = ""
            row["weaknesses"] = ""
            row["score"] = 0  # explicitly zero for invalid/empty/etc.
        else:
            # Ensure valid range 1..5 for non-zero scores
            if isinstance(row["score"], int):
                if row["score"] < 1: row["score"] = 1
                if row["score"] > 5: row["score"] = 5

        # Collect valid scores only (>0) for averaging
        if isinstance(row["score"], int) and row["score"] > 0:
            valid_scores.append(row["score"])

        by_order[order] = row

    # Rebuild ordered list
    normalized_answers = [by_order[o] for o in sorted(by_order)]

    # --- Session-level fields ---
    session["strengths"] = (session.get("strengths") or "").strip()
    session["weaknesses"] = (session.get("weaknesses") or "").strip()
    session["recommendation"] = (session.get("recommendation") or "").strip()

    # Average ONLY over valid (>0) scores; if none valid, overall=0.0
    if valid_scores:
        session["overall_score"] = round(sum(valid_scores) / len(valid_scores), 1)
    else:
        session["overall_score"] = 0.0

    return {"answers": normalized_answers, "session": session}


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