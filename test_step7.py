# -*- coding: utf-8 -*-
# test_step7.py — Step 7: 10 comments, EK EK baar (loop nahi), draft (koi post nahi).
# YouTube API call 0, POST 0. Offline: LLM classification band + FakeLLM.
# Result -> REPORT_3.md
#
# Chalao: venv\Scripts\python.exe test_step7.py

import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai
import knowledge
import mock_youtube
import pipeline
import reply_checks

# --- Offline setup (v2 jaisa) ---
mock_youtube.install_llm(mock_youtube.FakeLLM())
ai._llm_classify_course = lambda comment, records: None

# --- 10 comments (spec Step 7) ---
CASES = [
    {"id": "s7-01", "comment": "Ccc course ki fees?", "lang": "Roman Hinglish",
     "kind": "fee"},
    {"id": "s7-02", "comment": "CCC course ki fees aur duration kitna hai?",
     "lang": "Roman Hinglish", "kind": "fee"},
    {"id": "s7-03", "comment": "Kaha par h centre ?", "lang": "Roman Hinglish",
     "kind": "contact"},
    {"id": "s7-04", "comment": "Centre ka name ?", "lang": "Roman Hinglish",
     "kind": "institute_name"},
    {"id": "s7-05", "comment": "Editing vaigara ka koi course hota h yaha par?",
     "lang": "Roman Hinglish", "kind": "topic"},
    {"id": "s7-06", "comment": "Course ka naam kya hai?", "lang": "Roman Hinglish",
     "kind": "clarify"},
    {"id": "s7-07", "comment": "What is the fee of Python course?", "lang": "English",
     "kind": "fee_en"},
    {"id": "s7-08", "comment": "कंप्यूटर कोर्स की फीस कितनी है?",
     "lang": "Devanagari Hindi", "kind": "fee_hi"},
    {"id": "s7-09", "comment": "Bitcoin trading course karwana?",
     "lang": "Roman Hinglish", "kind": "not_in_list"},
    {"id": "s7-10", "comment": "Admission kaise le?", "lang": "Roman Hinglish",
     "kind": "admission"},
]

# Fee phrasing (spec): Hinglish "ki fee" / English "fee is" / Hindi "की फीस"
FEE_PHRASE = {
    "Roman Hinglish": "ki fee",
    "English": "fee is",
    "Devanagari Hindi": "की फीस",
}


def main():
    checks = []  # (name, ok, detail)

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if not ok else ""))

    top3 = [r["short_name"] for r in knowledge.course_records()[:3]]
    editing = [r["short_name"] for r in knowledge.group_courses("editing")]
    inst_name, inst_city = knowledge.institute_name_city()
    address = knowledge.contact_address()
    phone = knowledge.main_phone()
    adm_url = knowledge.admission_url()
    courses_url = knowledge.courses_page_url()

    rows = []
    for case in CASES:
        comment, lang = case["comment"], case["lang"]
        label, reply, _vid, reason = pipeline.handle_comment(
            comment, video_ctx=lambda: ("T", "C"),
            institute_enabled=True, notes_fn=lambda: "")
        reply = reply or ""
        print(f"\n[{case['id']}] {comment}")
        print(f"   label={label} reason={reason or '-'}")
        print(f"   reply: {reply or '(no reply)'}")
        rows.append((case, label, reply, reason))

        # --- Har reply par automatic checks ---
        check(f"{case['id']} label=institute_info", label == "institute_info", label)
        if not reply:
            check(f"{case['id']} reply hai", False, "(no reply)")
            continue

        fails, details = reply_checks.check_reply(comment, reply, lang)
        check(f"{case['id']} reply checks", not fails, str(details))
        check(f"{case['id']} language = comment jaisi",
              ai._detect_language(reply) == lang, ai._detect_language(reply))
        # ASCII " - " dash template se na aaye (address file ka data hai — wo alag)
        wo_addr = reply.replace(address, "") if address else reply
        check(f"{case['id']} ' - ' dash nahi", " - " not in wo_addr, reply)
        check(f"{case['id']} 'wale' nahi", "wale" not in reply.lower(), reply)
        check(f"{case['id']} 'India' nahi", "India" not in reply, reply)

        # Fee reply ho to sahi phrasing (spec: ki fee / fee is / की फीस)
        if "₹" in reply:
            phrase = FEE_PHRASE[lang]
            check(f"{case['id']} fee phrasing '{phrase}'", phrase in reply.lower(), reply)

        # --- Kind ke hisaab se specific checks ---
        kind = case["kind"]
        if kind == "fee":
            check(f"{case['id']} CCC fee value", "₹6,000" in reply, reply)
            check(f"{case['id']} galat 'list me nahi'", "list me nahi" not in reply, reply)
            if case["id"] == "s7-02":
                check(f"{case['id']} duration value", "3 Months" in reply, reply)

        elif kind == "contact":
            check(f"{case['id']} address hai", bool(address) and address in reply, reply)
            check(f"{case['id']} phone hai", phone in reply, reply)
            check(f"{case['id']} address pehle, phone baad me",
                  address in reply and phone in reply
                  and reply.index(address) < reply.index(phone), reply)

        elif kind == "institute_name":
            check(f"{case['id']} institute naam + city",
                  inst_name in reply and inst_city in reply, reply)

        elif kind == "admission":
            check(f"{case['id']} phone", phone in reply, reply)
            check(f"{case['id']} admission link", adm_url in reply, reply)

        elif kind == "topic":
            check(f"{case['id']} editing course ka naam",
                  any(n in reply for n in editing), reply)
            check(f"{case['id']} galat 'list me nahi'", "list me nahi" not in reply, reply)

        elif kind in ("clarify", "fee_en", "fee_hi"):
            # Specific course nahi mila (Python/kompyuter) = clarification —
            # fee value guess NAHI hoti (policy). Agar kabhi fee reply aayi to
            # "fee phrasing" check upar se ho chuka hai.
            check(f"{case['id']} popular courses + URL",
                  courses_url in reply and any(n in reply for n in top3), reply)
            check(f"{case['id']} galat 'list me nahi'", "list me nahi" not in reply, reply)

        elif kind == "not_in_list":
            check(f"{case['id']} 'list me ... nahi' (Bitcoin = sach)",
                  "list" in reply.lower() and "nahi" in reply.lower(), reply)
            check(f"{case['id']} phone", phone in reply, reply)

    # --- Sab replies par global checks ---
    print()
    all_replies = [r for _, _, r, _ in rows if r]
    check("kisi reply me 'wale' nahi", not any("wale" in r.lower() for r in all_replies))
    check("kisi reply me 'India' nahi", not any("India" in r for r in all_replies))

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nStep 7: {passed}/{len(checks)} CHECKS PASS")

    # --- REPORT_3.md (summary flags pehle — f-string me nested quotes nahi) ---
    fee_ok = all(ok for n, ok, _ in checks if "fee phrasing" in n)
    dash_ok = all(ok for n, ok, _ in checks if "' - ' dash" in n or "'wale'" in n)
    lang_ok = all(ok for n, ok, _ in checks if "language =" in n)
    india_ok = all(ok for n, ok, _ in checks if "India" in n)
    name_ok = all(ok for n, ok, _ in checks if "institute naam" in n)
    nolist_ok = all(ok for n, ok, _ in checks if "galat" in n)

    def _yn(ok):
        return "PASS" if ok else "FAIL"

    lines = [
        "# REPORT_3 — Step 7 test (10 comments)",
        "",
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- **Draft mode:** sirf pipeline test — YouTube API call **0**, POST **0**. "
        "Har comment EK baar chala (loop nahi).",
        "- Offline: LLM classification band (`ai._llm_classify_course -> None`) + FakeLLM.",
        "- Real knowledge file (`knowledge/zedking_info.md`) se values.",
        "",
        "## 10 comments — decision + reply",
        "",
        "| id | comment | label | reply | checks |",
        "|---|---|---|---|---|",
    ]
    for case, label, reply, reason in rows:
        cid = case["id"]
        case_checks = [(n, ok, d) for n, ok, d in checks if n.startswith(cid)]
        bads = [f"{n}: {d}" for n, ok, d in case_checks if not ok]
        if not reply:
            status = "FAIL — no reply"
        elif bads:
            status = "FAIL — " + "; ".join(bads)
        else:
            status = "PASS"
        c = case["comment"].replace("|", "\\|")
        r = (reply or "(no reply)").replace("|", "\\|")
        lines.append(f"| {cid} | {c} | {label} | {r} | {status} |")

    lines += [
        "",
        "## Checks (spec Step 7)",
        "",
        "- Fee replies me sahi phrasing (ki fee / fee is / की फीस): " + _yn(fee_ok),
        "- Kisi reply me ASCII ' - ' dash ya 'wale' nahi: " + _yn(dash_ok),
        "- Reply language comment ki language jaisi: " + _yn(lang_ok),
        "- Address me 'India' nahi: " + _yn(india_ok),
        "- institute_name sahi (naam + city): " + _yn(name_ok),
        "- Jahan matching course hai wahan galat 'list me nahi' nahi: " + _yn(nolist_ok),
        "",
        f"**Result:** {passed}/{len(checks)} checks PASS.",
        "",
        "### Notes",
        "",
        "- `What is the fee of Python course?` / `कंप्यूटर कोर्स की फीस कितनी है?` "
        "me specific course match nahi hota (ek hi weak candidate / koi nahi) — "
        "bot clarification deta hai, fee value guess NAHI karta (policy rule).",
        "- `Bitcoin trading course karwana?` = hamari list me sach me nahi — "
        "wahan sirf wahi 'list me nahi' sahi hai.",
    ]
    with open("REPORT_3.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("REPORT_3.md likha")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
