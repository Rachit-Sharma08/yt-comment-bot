# test_institute.py — institute pipeline ka test: label + chunks + reply
# YouTube par KUCH post nahi (draft only, koi DB save ya API call nahi).
# LLM call hoti hai (label + reply) — keys .env se aati hain.
# IMPORTANT: reply pipeline.py.handle_comment() se aata hai — wahi path jo
# main.py use karta hai (Step 6). Isliye test aur production hamesha same.
# Chalao: venv\Scripts\python.exe test_institute.py

import logging
import re  # no_fee / markdown / fee checks ke liye
import sys
import time  # cases ke beech delay — Groq/Gemini free tier rate-limit (429) se bachne ke liye

import ai  # _detect_language (reply ka language check ke liye)
import db  # contact cap ke liye table chahiye
import knowledge  # load_chunks + search + short_name
import pipeline  # comment -> reply ka shared path (main.py bhi yahi use karta hai)

# Windows console cp1252 hai — Devanagari/emoji print karne ke liye UTF-8 chahiye
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Warnings dikhao (discard/fail ka log) — keys kabhi print nahi hongi
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# Dummy video context — normal (non-institute) path me istemal hota hai
DUMMY_CONTEXT = "Sample video: daily vlog about computers and courses."

# Test cases (spec Step 7 ke 3 cases + pehle wale 2)
CASES = [
    "Zedking digital marketing ki fees ?",  # clarification (DMA ya AI Digital Pro)
    "Zedking ccc course ki fees?",  # exact course -> fee + course link
    "CCC course ki fees kitni hai aur admission",  # fee + admission intent
    "AI digital pro ki fees kitni hai?",  # exact course -> fee + course link
    "Aap konse institute padhte ho ?",  # personal_question -> SKIP
    "Tally course kitne mahine ka hai?",  # clarification
]

# Expected results — comment ke ek hisse se match hote hain
# label = intent label; reply = reply present; lang = reply ki language;
# no_fee = koi fee/duration number NAHI; fee = bada fee number (1000+) HAI
EXPECT = {
    "Zedking digital marketing ki fees": {
        "label": "institute_info", "reply": True, "lang": "Roman Hinglish",
        "no_fee": True,
    },
    "Zedking ccc course ki fees": {
        "label": "institute_info", "reply": True, "fee": True,
    },
    "CCC course ki fees kitni hai aur admission": {
        "label": "institute_info", "reply": True, "fee": True,
    },
    "AI digital pro ki fees kitni hai": {
        "label": "institute_info", "reply": True, "fee": True,
    },
    "Aap konse institute padhte ho": {
        "label": "personal_question", "reply": False,
    },
    "Tally course kitne mahine ka hai": {
        "label": "institute_info", "reply": True, "no_fee": True,
    },
}

# Reply me markdown bacha hona chahiye — heading/bullet line-start, bold,
# backtick, link, italic pairs. (Spec Step 1+7: plain text reply)
_MD_LEFT_RE = re.compile(
    r"(?m)^\s*(?:#|[-*])\s"  # line-start heading ya bullet
    r"|\*\*|__"  # bold markers
    r"|`"  # backticks
    r"|\[[^\]]+\]\("  # [text](url)
    r"|(?<![*\w])\*[^*\n]+\*(?!\*)"  # *italic*
    r"|(?<![\w_])_[^_\n]+_(?!_)"  # _italic_
)


def _has_markdown(reply):
    return bool(_MD_LEFT_RE.search(reply))


def _no_fee(reply):
    # Reply me fee/duration jaisa number NAHI — wahi check jo ai.py course gate
    # karta hai: phone ki formatting (+91-, spaces) hatao, 10+ digit = phone (OK),
    # usse chhota har digit-run = fee/amount/duration ka number (FAIL)
    norm = re.sub(r"[\s\-‐‑–—()+]", "", reply)
    for m in re.finditer(r"\d[\d,]*", norm):
        if len(re.sub(r"\D", "", m.group())) < 10:
            return False
    return True


def _has_fee(reply):
    # Fee ka bada number (1000+ par digit 4-9) — "10th"/"6 months" jaise chhote
    # number aur 10+ digit phone ye COUNT NAHI karte
    for m in re.finditer(r"\d[\d,]*", reply):
        d = re.sub(r"\D", "", m.group())
        if 4 <= len(d) <= 9 and int(d) >= 1000:
            return True
    return False


def _links(reply):
    """Reply me kitne links hain (spec Step 4: max ek link)."""
    return re.findall(r"(?i)https?://[^\s]+", reply)


def run_case(comment):
    """Ek comment par pipeline chala kar (label, reply, chunks, path) return karo.

    Wahi pipeline.handle_comment() jo main.py use karta hai — isliye test aur
    production ka reply hamesha same (Step 6).
    """
    db.init_db()  # contact cap (_contact_allowed) ko table chahiye

    label, reply, chunks, reason = pipeline.handle_comment(
        comment,
        video_ctx=lambda: ("Test Video", DUMMY_CONTEXT),
        institute_enabled=True,
    )
    if reason:
        return label, None, chunks, f"skip ({reason})"
    return label, reply, chunks, "institute (knowledge)"


def main():
    print("=" * 70)
    print("INSTITUTE PIPELINE TEST (draft only — YouTube par kuch nahi hoga)")
    print("=" * 70)

    # Knowledge file ek hi baar load (cache)
    chunks_all = knowledge.load_chunks()
    print(f"Knowledge chunks loaded: {len(chunks_all)}\n")

    # Spec Step 2: short_name mapping print (heading -> chhota naam)
    print("COURSE SHORT NAMES (heading -> short):")
    for c in chunks_all:
        if re.match(r"^\d+\.\s*", c["heading"]):
            print(f"  {c['heading'][:66]:66} -> {c['short']}")
    print()

    results = []  # (case, check, ok) — aakhir me PASS/FAIL summary
    for i, comment in enumerate(CASES, 1):
        print(f"--- Case {i}: {comment}")
        try:
            label, reply, chunks, path = run_case(comment)
        except Exception as e:
            # Crash nahi — case fail dikha kar aage badho
            print(f"    LABEL : ERROR ({e})")
            results.append((i, f"error: {e}", False))
            continue

        print(f"    LABEL : {label}")
        print(f"    PATH  : {path}")
        # Har case ki language: comment ki aur reply ki (Step 4 spec)
        print(f"    LANG  : comment={ai._detect_language(comment)} "
              f"reply={ai._detect_language(reply) if reply else '-'}")
        if chunks:
            # Kaun se chunks use hue — top 3 headings
            print(f"    CHUNKS: {[c['heading'][:50] for c in chunks]}")
        if reply is None:
            print("    REPLY : None (skip/discard/fail — upar reason dikhta hai)")
        else:
            print(f"    REPLY : {reply}")
            print(f"    LEN   : {len(reply)} chars, {reply.count(chr(10)) + 1} line(s), "
                  f"{len(_links(reply))} link(s)")

        # --- Expected results check (sirf naye cases EXPECT me hain) ---
        exp = next((e for key, e in EXPECT.items() if key in comment), None)
        if exp:
            if "label" in exp:
                results.append((i, f"label={exp['label']}",
                                label == exp["label"]))
            if "reply" in exp:
                results.append((i, "reply present" if exp["reply"] else "reply skip",
                                (reply is not None) == exp["reply"]))
            if "lang" in exp and reply:
                got = ai._detect_language(reply)
                results.append((i, f"reply lang={exp['lang']}", got == exp["lang"]))
            if exp.get("no_fee") and reply:
                results.append((i, "no fee number", _no_fee(reply)))
            if exp.get("fee") and reply:
                results.append((i, "fee number present", _has_fee(reply)))
        # Spec Step 1+7: har reply plain text — koi markdown bacha nahi hona chahiye
        if reply:
            results.append((i, "no markdown in reply", not _has_markdown(reply)))
            # Spec Step 4: max ek link per reply
            results.append((i, "max 1 link", len(_links(reply)) <= 1))
            # Spec Step 5: 280 char + 3 line limit
            results.append((i, "within 280 chars / 3 lines",
                            len(reply) <= 280 and reply.count("\n") <= 2))
        print()
        time.sleep(8)  # cases ke beech gap — free tier ke 429 se bachne ke liye

    print("=" * 70)
    print("CHECKS:")
    fails = 0
    for case_no, check, ok in results:
        print(f"  case {case_no}: {check} -> {'PASS' if ok else 'FAIL'}")
        fails += 0 if ok else 1
    print(f"TOTAL: {len(results) - fails}/{len(results)} PASS")
    print("TEST Khatam — upar har case ka label/lang/reply dekho.")
    print("Discard (None) = validator ne reply phenka — bot.log me reason hoga.")
    print("=" * 70)
    if fails:
        sys.exit(1)  # CI/test runner ke liye exit code


if __name__ == "__main__":
    main()
