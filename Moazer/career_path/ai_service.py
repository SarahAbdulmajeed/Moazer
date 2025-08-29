"""
AI adapter for the 'Discover Your Path' feature.

This module talks to OpenAI to:
- Generate phase-1 questions (School mode: broad across domains; Grad mode: within a university major).
- Pick a suggested path (School) or a precise subpath (Grad) from phase-1 answers.
- Generate phase-2 specialized questions based on the suggested (sub)path.
- Produce a final concise analysis (strengths, weaknesses, recommendation).

Design goals:
- Fail fast if OPENAI_API_KEY is missing.
- Keep outputs as plain strings; normalize arrays/objects defensively.
- Keep prompts short, deterministic, and Arabic-native.
"""

import os
import json
import re
from django.core.exceptions import ImproperlyConfigured

# --- Configuration / Initialization -------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

try:
    # Requires: pip install --upgrade openai
    from openai import OpenAI
except Exception as e:
    raise ImproperlyConfigured("OpenAI SDK is not installed. Run: pip install --upgrade openai") from e

# Lazily create the client. We validate presence of the key at call time via _require_client().
_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Canonical, user-facing Arabic labels for School mode classification.
PATH_LABELS = [
    "تقني",
    "صحي",
    "تعليمي",
    "إداري/أعمال",
    "إبداعي/تصميم",
    "هندسي",
]


def _require_client():
    """
    Ensure the OpenAI client is configured before any request.
    Raises an explicit configuration error if the API key is missing.
    """
    if not _client:
        raise ImproperlyConfigured("OPENAI_API_KEY is missing. Set it and restart the server.")


def _split_lines(text: str) -> list[str]:
    """
    Turn a model response into a clean list of items:
    - Split by newline.
    - Strip bullet characters and whitespace.
    - De-duplicate while preserving order.
    """
    lines = [ln.strip().lstrip("•-").strip() for ln in text.splitlines() if ln.strip()]
    uniq = []
    for q in lines:
        if q and q not in uniq:
            uniq.append(q)
    return uniq


# --- SCHOOL MODE -------------------------------------------------------------------

def generate_phase1_questions_school(n: int = 10) -> list[str]:
    """
    Generate 'n' broad discovery questions spanning PATH_LABELS for school/uni students.
    Returns a list of Arabic strings (one question per item).
    """
    _require_client()
    prompt = (
        f"اكتب {n} أسئلة عربية قصيرة لاكتشاف ميول الطالب المهنية تغطي عدة مسارات: "
        f"{', '.join(PATH_LABELS)}. اجعلها واضحة ومفتوحة النهاية. "
        "أعد كل سؤال في سطر مستقل، دون أرقام أو شروح."
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    lines = _split_lines(r.output_text)
    if len(lines) < n:
        raise RuntimeError("OpenAI returned fewer questions than requested (school p1).")
    return lines[:n]


def pick_suggested_path_from_phase1(answers_text: str) -> str:
    """
    Classify phase-1 answers into exactly one path from PATH_LABELS.
    Returns an Arabic label verbatim from PATH_LABELS.
    """
    _require_client()
    labels = ", ".join(PATH_LABELS)
    prompt = (
        "من خلال إجابات طالب على أسئلة عامة، اختر مسارًا واحدًا فقط "
        f"من القائمة التالية: [{labels}]. "
        "أعد JSON فقط بهذا الشكل: {\"path\": \"<أحد المسارات حرفيًا>\"}.\n\n"
        f"الإجابات:\n{answers_text}\n"
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    txt = r.output_text.strip()
    m = re.search(r"\{.*\}", txt, flags=re.S)
    if not m:
        raise RuntimeError("No JSON for suggested path.")
    obj = json.loads(m.group(0))
    path = (obj.get("path") or "").strip()
    if path not in PATH_LABELS:
        # Defensive: ensure consistent UI labels
        raise RuntimeError("Path not in PATH_LABELS.")
    return path


def generate_phase2_questions_school(suggested_path: str, n: int = 10) -> list[str]:
    """
    Generate 'n' specialized questions for the chosen high-level path (School mode).
    """
    _require_client()
    prompt = (
        f"اكتب {n} أسئلة عربية قصيرة متخصصة لمسار: {suggested_path}. "
        "كل سؤال في سطر مستقل، بدون أرقام."
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    lines = _split_lines(r.output_text)
    if len(lines) < n:
        raise RuntimeError("OpenAI returned fewer questions than requested (school p2).")
    return lines[:n]


# --- GRAD MODE (precise within a major) --------------------------------------------

def generate_phase1_questions_grad(major: str, n: int = 10) -> list[str]:
    """
    Generate 'n' general-but-within-major questions for graduates/candidates.
    Example major: 'علوم حاسب'.
    """
    _require_client()
    prompt = (
        f"اكتب {n} أسئلة عربية قصيرة لاستكشاف ميول مرشح داخل تخصصه الجامعي: {major}. "
        "الأسئلة عامة ولكن ضمن هذا التخصص، لإبراز التوجهات الدقيقة (مثال: أمن، ذكاء اصطناعي، تطوير...). "
        "أعد كل سؤال في سطر مستقل وبدون أرقام."
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    lines = _split_lines(r.output_text)
    if len(lines) < n:
        raise RuntimeError("OpenAI returned fewer questions than requested (grad p1).")
    return lines[:n]


def pick_subpath_within_major(major: str, answers_text: str) -> str:
    """
    Pick a single precise subpath INSIDE the supplied major (Arabic label).
    The subpath is model-generated, not restricted to a predefined list.
    """
    _require_client()
    prompt = (
        "استنادًا إلى إجابات مرشح داخل تخصص جامعي محدد، اختر مسارًا دقيقًا واحدًا (مثال في الحاسب: "
        "أمن سيبراني، تعلم الآلة/ذكاء اصطناعي، تطوير واجهات، تطوير خلفيات، علم البيانات، شبكات...). "
        "أعد JSON فقط: {\"subpath\": \"<المسار الدقيق بالعربية>\"}.\n\n"
        f"التخصص: {major}\n"
        f"الإجابات:\n{answers_text}\n"
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    txt = r.output_text.strip()
    m = re.search(r"\{.*\}", txt, flags=re.S)
    if not m:
        raise RuntimeError("No JSON for subpath.")
    obj = json.loads(m.group(0))
    subpath = (obj.get("subpath") or "").strip()
    if not subpath:
        raise RuntimeError("Empty subpath.")
    return subpath


def generate_phase2_questions_grad(subpath: str, n: int = 10) -> list[str]:
    """
    Generate 'n' specialized questions for the chosen precise subpath (Grad mode).
    """
    _require_client()
    prompt = (
        f"اكتب {n} أسئلة عربية قصيرة متخصصة لمسار دقيق: {subpath}. "
        "كل سؤال في سطر مستقل، بدون أرقام."
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    lines = _split_lines(r.output_text)
    if len(lines) < n:
        raise RuntimeError("OpenAI returned fewer questions than requested (grad p2).")
    return lines[:n]


# --- Final analysis (shared across modes) ------------------------------------------

def _as_text(value) -> str:
    """
    Normalize any model-returned value (list/dict/str) into a compact Arabic string:
    - list/tuple -> comma-joined string
    - dict -> compact JSON string (ensure_ascii=False)
    - other -> stripped str(value)
    """
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_as_text(v) for v in value if v is not None)
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return str(value)
    return str(value).strip()


def analyze_final_result(suggested_path: str, answers_text: str) -> dict:
    """
    Produce a concise final report in Arabic.
    Returns a dict with the keys: strengths, weaknesses, recommendation (all strings).
    """
    _require_client()
    prompt = (
        "حلّل إجابات مختصرة وأعد JSON فقط بالمفاتيح: strengths, weaknesses, recommendation. "
        "اجعل القيم نصًا عربيًا موجزًا، وإذا تعددت النقاط افصلها بفواصل.\n\n"
        f"المسار المقترح: {suggested_path}\n"
        f"الإجابات:\n{answers_text}\n"
    )
    r = _client.responses.create(model="gpt-4o-mini", input=prompt)
    txt = r.output_text.strip()
    m = re.search(r"\{.*\}", txt, flags=re.S)
    obj = json.loads(m.group(0) if m else txt)
    return {
        "strengths": _as_text(obj.get("strengths")),
        "weaknesses": _as_text(obj.get("weaknesses")),
        "recommendation": _as_text(obj.get("recommendation")),
    }
