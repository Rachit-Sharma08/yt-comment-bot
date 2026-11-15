# test_institute_v2.py — Step 5: 16 comments, REAL knowledge file, offline.
# YouTube API call 0, POST 0. LLM sirf classification ke liye hoti hai — yahan
# band hai (ai._llm_classify_course -> None), taaki test free aur deterministic rahe.
#
# Chalao: venv\Scripts\python.exe test_institute_v2.py

import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai
import config
import knowledge
import mock_youtube
import pipeline
import reply_checks

# --- 16 cases: values knowledge file ke record se exactly match hone chahiye ---
CASES = [
    {"id": "v2-01", "comment": "CCC course ki fees kitni hai?", "label": "institute_info",
     "value": ("fee", "CCC", "₹6,000"), "lang": "Roman Hinglish"},
    {"id": "v2-02", "comment": "CCC course ki fees aur duration kitni hai?",
     "label": "institute_info",
     "values": [("fee", "CCC", "₹6,000"), ("duration", "CCC", "3 Months")],
     "lang": "Roman Hinglish"},
    {"id": "v2-03", "comment": "Python course ki eligibility kya hai?", "label": "institute_info",
     "ask_course": True, "lang": "Roman Hinglish"},
    {"id": "v2-04", "comment": "Tally course kitne mahine ka hai?", "label": "institute_info",
     "ask_course": True, "lang": "Roman Hinglish"},
    {"id": "v2-05", "comment": "digital marketing ki fees", "label": "institute_info",
     "ask_course": True, "lang": "Roman Hinglish"},
    {"id": "v2-06", "comment": "AI Digital Pro ki fees kitni hai?", "label": "institute_info",
     "value": ("fee", "AI Digital Pro", "₹35,000"), "lang": "Roman Hinglish"},
    {"id": "v2-07", "comment": "Bitcoin trading course karwana?", "label": "institute_info",
     "phone": True, "lang": "Roman Hinglish"},
    {"id": "v2-08", "comment": "Fire safety course ki eligibility?", "label": "institute_info",
     "phone": True, "lang": "Roman Hinglish"},
    {"id": "v2-09", "comment": "Address kya hai institute ka?", "label": "institute_info",
     "phone": True, "lang": "Roman Hinglish"},
    {"id": "v2-10", "comment": "admission kaise le", "label": "institute_info",
     "phone": True, "lang": "Roman Hinglish"},
    {"id": "v2-11", "comment": "फीस कितनी है?", "label": "institute_info",
     "ask_course": True, "lang": "Devanagari Hindi"},
    {"id": "v2-12", "comment": "What is the duration of CCC?", "label": "institute_info",
     "value": ("duration", "CCC", "3 Months"), "lang": "English"},
    {"id": "v2-13", "comment": "Which camera did you use?", "label": "video_question",
     "reason": "needs_owner", "lang": "English"},
    {"id": "v2-14", "comment": "Nice video bro", "label": "praise", "lang": "English"},
    {"id": "v2-15", "comment": "Bot ho kya?", "label": "asks_if_bot",
     "reason": "asks_if_bot", "lang": "Roman Hinglish"},
    {"id": "v2-16", "comment": "Aap kahan rehte ho?", "label": "personal_question",
     "reason": "personal_question", "lang": "Roman Hinglish"},
]

# Checks: "no_value" = reply me koi number nahi (sirf course ka naam poochha)
_NO_VALUE_FIELDS = ("fee", "duration", "eligibility", "mode", "certificate")


def _record_value(field, course_short):
    """Knowledge file se us course ka field value (grounding check ke liye)."""
    for r in knowledge.course_records():
        if r["short_name"] == course_short:
            return r.get(field)
    return None


def _numbers(text):
    return re.findall(r"\d[\d,]*", text or "")


def _is_phone_only(text):
    """Reply me phone ke alawa koi number nahi (address ka PIN bhi allowed)."""
    clean = (text or "").replace(knowledge.main_phone(), "")
    clean = clean.replace(knowledge.contact_address(), "")
    for tok in _numbers(clean):
        digits = re.sub(r"\D", "", tok)
        if len(digits) < 10:
            return False
    return True


def _run_case(case):
    """Ek comment pipeline se chalao (wahi path jo main.py use karta hai)."""
    label, reply, chunks, reason = pipeline.handle_comment(
        case["comment"],
        video_ctx=lambda: ("Test Video", "Test video ka context."),
        institute_enabled=True,
        notes_fn=lambda: "",
    )
    return label, reply, reason


def _owner_fact_tests():
    """Owner facts: temp copy me fact daal ke jawab aaye + khali facts par skip."""
    results = []
    tmp = Path(tempfile.gettempdir()) / "ytbot_owner_facts_test.md"
    tmp.write_text(
        "Camera / phone (jisse vlog shoot hota hai): TEST PHONE X\n"
        "Mic:\n",
        encoding="utf-8",
    )
    old_file = config.OWNER_FACTS_FILE
    try:
        # --- 1) fact daala hai -> jawab fact se aaye ---
        config.OWNER_FACTS_FILE = str(tmp)
        knowledge._OWNER_FACTS = None  # cache reset
        mock_youtube.install_llm(mock_youtube.FakeLLM())
        label, reply, reason = _run_case(
            {"id": "owner-1", "comment": "Kaunsa camera tha?"})
        ok = bool(reply) and "TEST PHONE X" in reply and reason == ""
        results.append(("owner_facts me fact = reply me fact", ok,
                        reply or f"({reason})"))

        # --- 2) facts khali -> needs_owner (reply nahi) ---
        empty = Path(tempfile.gettempdir()) / "ytbot_owner_facts_empty.md"
        empty.write_text("Camera / phone (jisse vlog shoot hota hai):\n", encoding="utf-8")
        config.OWNER_FACTS_FILE = str(empty)
        knowledge._OWNER_FACTS = None
        label, reply, reason = _run_case(
            {"id": "owner-2", "comment": "Kaunsa camera tha?"})
        ok = reply is None and reason == "needs_owner"
        results.append(("facts khali = needs_owner skip (no reply)", ok,
                        f"reason={reason} reply={reply}"))
    finally:
        config.OWNER_FACTS_FILE = old_file
        knowledge._OWNER_FACTS = None
    return results


def main():
    # Offline: LLM classification band + mock LLM (reply ke liye)
    ai._llm_classify_course = lambda comment, records: None
    mock_youtube.install_llm(mock_youtube.FakeLLM())

    checks, rows = [], []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if not ok else ""))

    for case in CASES:
        label, reply, reason = _run_case(case)
        print(f"\n[{case['id']}] {case['comment']}")
        print(f"   label={label} reason={reason or '-'}")
        print(f"   reply: {reply or '(no reply)'}")

        # 1) decision sahi hai?
        check(f"{case['id']} label={case['label']}", label == case["label"], label)
        if "reason" in case:
            check(f"{case['id']} reason={case['reason']}", reason == case["reason"], reason)
            check(f"{case['id']} koi reply nahi", reply is None, str(reply))

        if reply:
            # 2) automatic checks (markdown/glued/internal/promise/AI-phrase/
            #    em dash/third-person/link/280 char/language)
            fails, details = reply_checks.check_reply(
                case["comment"], reply, case["lang"])
            check(f"{case['id']} reply checks", not fails, str(details))

            # 3) value file se exactly match
            for field, course, value in (case.get("values") or
                                         ([case["value"]] if case.get("value") else [])):
                real = _record_value(field, course)
                ok = real == value and value.lower() in reply.lower()
                check(f"{case['id']} {field} value file se match ({value})", ok,
                      f"file={real} reply_has={value.lower() in reply.lower()}")

            # 4) sirf course ka naam poocha (koi number nahi)
            if case.get("ask_course"):
                low = reply.lower()
                asks = ("naam" in low or "name" in low or "likh" in low
                        or "नाम" in reply or "बताइए" in reply or "?" in reply)
                ok = (not _numbers(reply)) and asks
                check(f"{case['id']} course ka naam poochha (number nahi)", ok, reply)

            # 5) phone wali replies me sirf phone number
            if case.get("phone"):
                ok = knowledge.main_phone() in reply and _is_phone_only(reply)
                check(f"{case['id']} phone (aur koi number nahi)", ok, reply)

        rows.append((case, label, reply, reason))

    # --- Owner facts ke 2 test ---
    print()
    for name, ok, detail in _owner_fact_tests():
        check(name, ok, detail)

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nInstitute v2: {passed}/{len(checks)} PASS")

    # --- REPORT_2.md ---
    lines = [
        "# REPORT_2 — Institute v2 + voice/facts test (Step 5)",
        "",
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- Real knowledge file (`knowledge/zedking_info.md`) se values — koi hardcode value nahi.",
        "- YouTube API call **0**, POST **0**. LLM sirf classification ke liye hoti hai — "
        "test me band hai (offline + deterministic).",
        "- Har reply par automatic checks: markdown, glued word, internal word, promise "
        "(vaada), AI-jaisa phrase, em dash, third-person 'ZedKing ke ...', link count/domain, "
        "280 char, comment ki language.",
        "",
        "## 16 comments — decision + reply",
        "",
        "| ID | Comment | Label | Reply | Checks |",
        "|---|---|---|---|---|",
    ]
    for case, label, reply, reason in rows:
        fails, _ = reply_checks.check_reply(case["comment"], reply, case["lang"]) if reply else ([], {})
        mark = "PASS" if not fails else "FAIL: " + ", ".join(fails)
        lines.append(f"| {case['id']} | {case['comment']} | {label} | "
                     f"{(reply or '(no reply)').replace('|', '/')} | {mark} |")
    lines += ["", "## Checks", "", "| Check | Result |", "|---|---|"]
    for name, ok, detail in checks:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL' + (' — ' + detail if detail else '')} |")
    lines += ["", f"**Total: {passed}/{len(checks)} PASS**"]
    Path("REPORT_2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("REPORT_2.md likha")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
