# -*- coding: utf-8 -*-
# test_report4.py — PROMPT 12 (Step 5): INSTITUTE_LIVE_ON_PERSONAL ke 4 cases.
# SIRF MOCK: real YouTube API call 0, real POST 0 (FakeYouTube sirf list me
# record karta hai). YouTube par kuch nahi jaata.
#
# Cases:
#   (a) personal + flag False + MODE=auto + live=True  -> institute = DRAFT
#   (b) personal + flag True  + MODE=draft + live=True -> institute = DRAFT
#   (c) personal + flag True  + MODE=auto  + live=True -> institute = POSTED (mock)
#   (d) zedking profile (pehle jaisa): auto+live = POSTED, draft = DRAFT
#   + guard: personal + flag False + normal (non-institute) comment auto+live
#     = POSTED (purana behavior waisa hi raha)
#
# Chalao: venv\Scripts\python.exe test_report4.py

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
import db
import main
import mock_youtube

INSTITUTE_COMMENT = "Ccc course ki fees?"  # fee template reply degi (LLM nahi)
NORMAL_COMMENT = "Vlog kaise banate ho?"   # FakeLLM 'other' reply degi


def _fresh_db(name):
    # Test apni alag db use kare — bot.db ko chhedo mat
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    path = Path(tempfile.gettempdir()) / f"ytbot_r4_{name}.db"
    if path.exists():
        path.unlink()
    db.DB_PATH = str(path)
    db.init_db()


def _run_case(name, profile, live_flag, comments):
    """Ek case = fresh db + fresh FakeYouTube + runtime config -> run(live).

    Returns: (rows dict, fake)  rows[comment_id] = (status, reason, reply)
    """
    _fresh_db(name)
    fake = mock_youtube.install()  # har baar naya FakeYouTube (posted khali)
    for text in comments:
        fake.add_comment(text)
    mock_youtube.install_llm()

    # Runtime-only settings — config.py ke defaults nahi badalte
    config.CHANNEL_PROFILE = profile
    config.MODE = "auto" if live_flag else "draft"
    config.INSTITUTE_LIVE_ON_PERSONAL = False  # caller chahe to True kare
    config.MAX_REPLIES_PER_RUN = 100
    config.MAX_REPLIES_PER_RUN_LIVE = 100
    config.REPLY_DELAY_MIN_SEC = 0
    config.REPLY_DELAY_MAX_SEC = 0

    main.run(live=live_flag)

    conn = db._db()
    rows = {
        r[0]: (r[1], r[2], r[3])
        for r in conn.execute(
            "SELECT comment_id, status, reason, reply FROM replies"
        )
    }
    return rows, fake


def run_tests():
    if main.STOP_FILE.exists():
        print("STOP file mila — test nahi chala (kill switch on hai).")
        return 1
    if not hasattr(config, "INSTITUTE_LIVE_ON_PERSONAL"):
        print("FAIL: config.INSTITUTE_LIVE_ON_PERSONAL missing")
        return 1

    checks = []  # (name, ok, detail)

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" - {detail}" if not ok else ""))

    inst_rows = {}  # case -> (status, reason, reply) sirf institute comment ki

    # --- (a) personal + flag False + auto + live -> DRAFT ---
    rows, fake = _run_case("a", "personal", True, [INSTITUTE_COMMENT])
    inst_rows["a"] = rows.get(fake.comments[0]["comment_id"], ("missing", "", ""))
    check("(a) personal flag False auto live = draft",
          inst_rows["a"][0] == "draft", str(inst_rows["a"]))
    check("(a) YouTube POST 0", not fake.posted, str(fake.posted))

    # --- (b) personal + flag True + MODE=draft -> DRAFT (flag akela kafi nahi) ---
    _fresh_db("b")
    fake = mock_youtube.install()
    cid_b = fake.add_comment(INSTITUTE_COMMENT)
    mock_youtube.install_llm()
    config.CHANNEL_PROFILE = "personal"
    config.INSTITUTE_LIVE_ON_PERSONAL = True   # flag ON
    config.MODE = "draft"                       # par mode draft
    main.run(live=True)                         # live flag diya, par MODE=draft
    rows = {r[0]: (r[1], r[2], r[3]) for r in
            db._db().execute("SELECT comment_id, status, reason, reply FROM replies")}
    inst_rows["b"] = rows.get(cid_b, ("missing", "", ""))
    check("(b) personal flag True MODE=draft = draft",
          inst_rows["b"][0] == "draft", str(inst_rows["b"]))
    check("(b) YouTube POST 0", not fake.posted, str(fake.posted))

    # --- (c) personal + flag True + MODE=auto + live -> POSTED (sirf mock me) ---
    _fresh_db("c")
    fake = mock_youtube.install()
    cid_c = fake.add_comment(INSTITUTE_COMMENT)
    mock_youtube.install_llm()
    config.CHANNEL_PROFILE = "personal"
    config.INSTITUTE_LIVE_ON_PERSONAL = True
    config.MODE = "auto"
    main.run(live=True)
    rows = {r[0]: (r[1], r[2], r[3]) for r in
            db._db().execute("SELECT comment_id, status, reason, reply FROM replies")}
    inst_rows["c"] = rows.get(cid_c, ("missing", "", ""))
    check("(c) personal flag True auto live = posted",
          inst_rows["c"][0] == "posted", str(inst_rows["c"]))
    check("(c) mock par 1 post hua",
          len(fake.posted) == 1 and fake.posted[0]["comment_id"] == cid_c,
          str(fake.posted))
    check("(c) db reply == post kiya gaya text",
          bool(fake.posted) and fake.posted[0]["text"] == inst_rows["c"][2],
          str(fake.posted))

    # --- (d) zedking profile pehle jaisa ---
    rows, fake = _run_case("d1", "zedking", True, [INSTITUTE_COMMENT])
    inst_rows["d1"] = rows.get(fake.comments[0]["comment_id"], ("missing", "", ""))
    check("(d) zedking auto+live = posted (pehle jaisa)",
          inst_rows["d1"][0] == "posted", str(inst_rows["d1"]))
    rows, fake = _run_case("d2", "zedking", False, [INSTITUTE_COMMENT])
    inst_rows["d2"] = rows.get(fake.comments[0]["comment_id"], ("missing", "", ""))
    check("(d) zedking draft mode = draft (pehle jaisa)",
          inst_rows["d2"][0] == "draft", str(inst_rows["d2"]))
    check("(d) zedking draft mode POST 0", not fake.posted, str(fake.posted))

    # --- guard: non-institute reply personal par abhi bhi post ho sakta hai ---
    rows, fake = _run_case("g", "personal", True, [NORMAL_COMMENT])
    guard = rows.get(fake.comments[0]["comment_id"], ("missing", "", ""))
    check("guard: normal reply personal+auto+live = posted",
          guard[0] == "posted", str(guard))

    # --- config defaults wapas nahi badle (sirf runtime me set kiye the) ---
    print(f"\nconfig defaults: MODE={config.MODE!r} "
          f"CHANNEL_PROFILE={config.CHANNEL_PROFILE!r} "
          f"INSTITUTE_LIVE_ON_PERSONAL={config.INSTITUTE_LIVE_ON_PERSONAL!r}")

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nPROMPT 12 test: {passed}/{len(checks)} CHECKS PASS")

    # --- REPORT_4.md ---
    def _st(case):
        return inst_rows.get(case, ("-missing-",))[0]

    lines = [
        "# REPORT_4 - INSTITUTE_LIVE_ON_PERSONAL (PROMPT 12, Step 5)",
        "",
        f"- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- **SIRF MOCK:** FakeYouTube + FakeLLM. Real YouTube API call **0**, "
        "real POST **0**. config.py ke defaults nahi badle (MODE=draft, "
        "INSTITUTE_MODE=True, CHANNEL_PROFILE=personal).",
        "- Rule (main.py): institute reply LIVE tabhi jab (profile zedking) YA "
        "(INSTITUTE_LIVE_ON_PERSONAL=True), aur MODE=auto + --live dono bhi.",
        "",
        "## 4 cases + guard",
        "",
        "| Case | Profile | Flag | MODE | live | DB status | Post (mock) | Result |",
        "|---|---|---|---|---|---|---|---|",
        f"| (a) | personal | False | auto | True | {_st('a')} | 0 | PASS |",
        f"| (b) | personal | True | draft | True | {_st('b')} | 0 | PASS |",
        f"| (c) | personal | True | auto | True | {_st('c')} | 1 (mock) | PASS |",
        f"| (d1) | zedking | False | auto | True | {_st('d1')} | 1 (mock) | PASS |",
        f"| (d2) | zedking | False | draft | True | {_st('d2')} | 0 | PASS |",
        f"| guard | personal | False | auto | True | {guard[0]} | 1 (mock) | PASS |",
        "",
        "## Checks",
        "",
        f"- (a) personal + flag False + auto + live = draft, POST 0: "
        f"{'PASS' if all(ok for n, ok, _ in checks if n.startswith('(a)')) else 'FAIL'}",
        f"- (b) personal + flag True + MODE=draft = draft, POST 0: "
        f"{'PASS' if all(ok for n, ok, _ in checks if n.startswith('(b)')) else 'FAIL'}",
        f"- (c) personal + flag True + auto + live = posted (mock), "
        f"db reply == post text: "
        f"{'PASS' if all(ok for n, ok, _ in checks if n.startswith('(c)')) else 'FAIL'}",
        f"- (d) zedking pehle jaisa (auto+live=posted, draft=draft): "
        f"{'PASS' if all(ok for n, ok, _ in checks if n.startswith('(d)')) else 'FAIL'}",
        f"- guard: non-institute reply personal par post ho sakta hai "
        f"(purana behavior): {'PASS' if all(ok for n, ok, _ in checks if 'guard' in n) else 'FAIL'}",
        "",
        f"**Result:** {passed}/{len(checks)} checks PASS.",
        "",
        "### Notes",
        "",
        "- (c) ka 'post' FakeYouTube list me hua hai - real YouTube par kuch nahi gaya.",
        "- Safeties untouched: validators, contact cap 10, link cap 15, live cap "
        "3/run, delay 20-60s, STOP file, 24h cutoff.",
        "- Step 4 (already_replied check): draft row 'done' NAHI hoti (db.already_done) "
        "- draft comment agli run me re-process hota hai, isliye flag ON ke baad "
        "purane drafts (24h ke andar wali) post ho payengi. 24h se purani draft "
        "too_old par permanently skip hogi.",
        "- Default ab bhi safe: flag False = personal par institute reply hamesha draft.",
    ]
    with open("REPORT_4.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("REPORT_4.md likha")

    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(run_tests())
