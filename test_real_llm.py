# test_real_llm.py — Step 5: reply quality REAL LLM se check karo (Groq/Gemini).
# Sirf LLM ki network call hoti hai — YouTube API bilkul nahi (youtube.py import bhi nahi).
# 12 real calls, beech me 8 sec gap. 429 aaye to 60 sec ruk kar EK retry.
#
# Chalao: venv\Scripts\python.exe test_real_llm.py

import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai
import config
import db
import knowledge
import reply_checks
import report_utils

GAP_SEC = 8            # do calls ke beech gap (rate-limit se bachne ke liye)
RATE_LIMIT_WAIT = 60   # 429 aaye to itna ruk kar ek hi retry

# Video context — jaan-bujh kar camera/mic/software ka naam NAHI likha, taaki
# model ko "pata nahi" bolna pade (hallucination pakadne ke liye)
VIDEO_TITLE = "Kaithal Vlog #12 — Naya Studio Setup aur Aaj Ka Din"
VIDEO_CONTEXT = (
    "Aaj ke vlog me hum apne naye studio ka tour karwa rahe hain, Kaithal me. "
    "Bataya ki studio banane me kitna time laga, kaunsi cheezein setup ki, aur "
    "aage kaunse videos aa rahe hain. Beech me ek chhota sa time-lapse bhi dikhaya."
)

# kind: "video" = make_reply, "institute" = knowledge.search + answer_institute
# expect: "check" = "dekh ke batata hoon" jaisa jawab, "thanks" = thank-you (check nahi),
#         "fact" = values me se koi ek reply me hona chahiye
CASES = [
    {"id": "llm-01", "kind": "video", "expect": "check",
     "text": "Bhai ye vlog kis camera se shoot kiya?"},
    {"id": "llm-02", "kind": "video", "expect": "check",
     "text": "Which camera did you use?"},
    {"id": "llm-03", "kind": "video", "expect": "check",
     "text": "यह वीडियो किस कैमरे से शूट हुआ है?"},
    {"id": "llm-04", "kind": "video", "expect": "check",
     "text": "Is video me konsa mic use kiya?"},
    {"id": "llm-05", "kind": "video", "expect": "check",
     "text": "What editing software do you use?"},
    {"id": "llm-06", "kind": "video", "expect": "thanks",
     "text": "Nice video bro"},
    {"id": "llm-07", "kind": "video", "expect": "thanks",
     "text": "Bahut achha video tha bhai"},
    {"id": "llm-08", "kind": "video", "expect": "thanks",
     "text": "बहुत बढ़िया वीडियो"},
    {"id": "llm-09", "kind": "institute", "expect": "fact",
     "values": ["6,000"],
     "text": "CCC course ki fees kitni hai?"},
    {"id": "llm-10", "kind": "institute", "expect": "fact",
     "values": ["6 month", "6 mahine", "6 महीने"],
     "text": "Digital marketing course ki duration kitni hai?"},
    {"id": "llm-11", "kind": "institute", "expect": "fact",
     "values": ["10th", "10वीं", "10 वीं"],
     "text": "Digital marketing course ki eligibility kya hai?"},
    {"id": "llm-12", "kind": "institute", "expect": "fact",
     "values": ["kaithal"],
     "text": "Institute ka address kya hai?"},
]

# --- 429 pakadne ke liye chhota wrapper (make_reply exception nigal jaata hai) ---
_rate_limited = {"hit": False}


def _watch_429(fn):
    def inner(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            resp = getattr(e, "response", None)
            if getattr(resp, "status_code", None) == 429:
                _rate_limited["hit"] = True
            raise
    return inner


def _fresh_db():
    # Contact/link cap counters test ki apni db me — bot.db ko chhedo mat
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    path = Path(tempfile.gettempdir()) / "ytbot_real_llm.db"
    if path.exists():
        path.unlink()
    db.DB_PATH = str(path)
    db.init_db()


_CHECK_RE = re.compile(
    r"(?i)dekh|check|bata|pata|jankari|confirm|look into|let you know|जानकारी|बत|देख"
)
_THANKS_RE = re.compile(r"(?i)thank|shukriya|dhanyavad|शुक्रिया|धन्यवाद|khushi|glad|happy|बढ़िया")
# Praise reply me ye promise-phrases nahi hone chahiye ("dekh ke" akela false
# positive tha — "Khush kar diya dekh ke" bhi valid thank-you hai)
_PROMISE_RE = re.compile(
    r"(?i)dekh\s*(?:ke|kar)\s*(?:bata|check)|check\s*(?:kar|ke)|let you know"
    r"|bata\s*(?:doonga|dunga|denge)|jankari\s*(?:le|de)|pata\s*kar"
    r"|पता\s*(?:कर|ल)|जानकारी\s*(?:ले|द)|देख\s*(?:कर|के)\s*बत"
)


def _norm(text):
    # NBSP + extra spaces + comma hata do — "6,000" vs "6 000" vs "6\u00a0000"
    return re.sub(r"\s+", " ", (text or "").lower().replace("\u00a0", " ")).replace(",", "")


def _expect_ok(case, reply):
    """Soft quality signal — reply ne comment ka type sahi samjha?"""
    if not reply:
        return False
    if case["expect"] == "check":
        return bool(_CHECK_RE.search(reply))
    if case["expect"] == "thanks":
        # Praise par "dekh ke batata hoon" nahi hona chahiye
        return bool(_THANKS_RE.search(reply) and not _PROMISE_RE.search(reply))
    low = _norm(reply)
    return any(_norm(v) in low for v in case["values"])


def _ask(case):
    if case["kind"] == "video":
        return ai.make_reply(VIDEO_TITLE, VIDEO_CONTEXT, case["text"])
    chunks = knowledge.search(case["text"], top_k=3)
    return ai.answer_institute(case["text"], chunks)


def _run_case(case):
    _rate_limited["hit"] = False
    ai.LAST_MODEL = None
    reply = _ask(case)
    retried = False
    if reply is None and _rate_limited["hit"]:
        retried = True
        print(f"  429 mila — {RATE_LIMIT_WAIT}s ruk kar ek retry...")
        time.sleep(RATE_LIMIT_WAIT)
        _rate_limited["hit"] = False
        ai.LAST_MODEL = None
        reply = _ask(case)
    return reply, ai.LAST_MODEL, retried


def _cell(text, limit=220):
    s = str(text or "").replace("|", "\\|").replace("\n", " / ")
    return s[: limit - 1] + "…" if len(s) > limit else s


def _write_skip(reason):
    report_utils.write_section(
        "STEP5",
        "## Step 5 — Real LLM quality test\n\n"
        f"- Status: **SKIPPED**\n- Reason: {reason}\n"
        "- Koi network call nahi hui. `.env` me `GROQ_API_KEY` ya "
        "`GEMINI_API_KEY` daal kar `venv\\Scripts\\python.exe test_real_llm.py` "
        "dobara chalao.",
    )


def main():
    if not config.GROQ_API_KEY and not config.GEMINI_API_KEY:
        print("SKIP: .env me GROQ_API_KEY / GEMINI_API_KEY dono khali hain — real LLM test nahi chala.")
        _write_skip("dono API keys khali hain (`.env` me set nahi).")
        return 0

    providers = []
    if config.GROQ_API_KEY:
        providers.append("Groq")
    if config.GEMINI_API_KEY:
        providers.append("Gemini")
    print(f"Real LLM test: {len(CASES)} cases, providers={providers}, gap={GAP_SEC}s\n")

    _fresh_db()
    ai._call_groq = _watch_429(ai._call_groq)
    ai._call_gemini = _watch_429(ai._call_gemini)

    rows, got, hard_fail, expect_miss, used = [], 0, 0, 0, []
    all_chunks = knowledge.load_chunks()

    for i, case in enumerate(CASES):
        print(f"[{case['id']}] {case['text']}")
        reply, model, retried = _run_case(case)

        fails, details = reply_checks.check_reply(
            case["text"], reply, ai._detect_language(case["text"])
        )
        if not reply:
            fails = ["no_reply"] + fails
        # Institute reply ke number/link/address knowledge me grounded hone chahiye
        if reply and case["kind"] == "institute":
            ok, why = ai._facts_in_chunks(reply, all_chunks)
            if not ok:
                fails.append("facts_not_grounded")
                details["facts_not_grounded"] = why

        exp_ok = _expect_ok(case, reply)
        got += bool(reply)
        hard_fail += bool(fails)
        expect_miss += not exp_ok
        if model:
            used.append(model)

        print(f"   model={model or '-'} retry={retried} checks={'PASS' if not fails else fails} "
              f"expect={'OK' if exp_ok else 'MISS'}")
        print(f"   reply: {reply}\n")

        rows.append(
            f"| {case['id']} | {case['kind']} | {_cell(case['text'], 60)} | "
            f"{_cell(reply)} | {model or '-'} | "
            f"{'PASS' if not fails else ', '.join(fails)} | "
            f"{'OK' if exp_ok else 'MISS'} |"
        )

        if i < len(CASES) - 1:
            time.sleep(GAP_SEC)  # agle call se pehle gap

    total = len(CASES)
    models = ", ".join(f"{m} x{used.count(m)}" for m in sorted(set(used))) or "koi nahi"

    table = (
        "## Step 5 — Real LLM quality test\n\n"
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"- Providers: {', '.join(providers)} | Model: `{config.GROQ_MODEL}` / "
        f"`{config.GEMINI_MODEL}`\n"
        f"- Cases: {total} | Reply bana: {got} | Hard fail: {hard_fail} | "
        f"Expectation miss: {expect_miss}\n"
        f"- Kis model ne jawab diya: {models}\n"
        "- Har case me 8 sec gap; 429 par ek hi retry (60 sec baad). "
        "YouTube API call nahi hui — sirf LLM.\n\n"
        "| ID | Type | Comment | Reply | Model | Auto checks | Expect |\n"
        "|---|---|---|---|---|---|---|\n" + "\n".join(rows)
    )
    report_utils.write_section("STEP5", table)

    print(f"\nTotal {total} | reply {got} | hard fail {hard_fail} | expect miss {expect_miss}")
    return 0 if got == total and hard_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
