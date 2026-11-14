# test_review.py — Step 6: review.py --stats / --today ka test (temp db, koi network nahi)
# Chalao: venv\Scripts\python.exe test_review.py

import contextlib
import io
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import db
import report_utils
import review

LONG_COMMENT = "Bahut lamba comment " * 12  # 240 char — drafts me poora dikhna chahiye


def _fresh_db(name="ytbot_review.db"):
    # Har test apni temp db — bot.db ko chhedo mat
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    path = Path(tempfile.gettempdir()) / name
    if path.exists():
        path.unlink()
    db.DB_PATH = str(path)
    db.init_db()


def _run(*args):
    """review.py ko diye gaye args ke saath chalao aur output wapas do."""
    old = sys.argv
    sys.argv = ["review.py", *args]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            review.main()
    finally:
        sys.argv = old
    return buf.getvalue()


def _seed():
    rows = [
        ("c1", "draft", "institute", "CCC course ki fees?", "CCC ki fee ₹6,000 hai."),
        ("c2", "draft", "llm", "Nice video", "Thanks!"),
        ("c3", "draft", "emoji", "🔥", "Shukriya!"),
        ("c4", "posted", "institute", "Address?", "Kaithal me hain."),
        ("c5", "posted", "llm", "Great", "Thank you!"),
        ("c6", "skipped", "spam_link", "http://spam.xyz", ""),
        ("c7", "failed", "llm_fail", "Question?", ""),
        ("c8", "draft", "institute", LONG_COMMENT, "Purana draft reply"),
    ]
    for cid, status, reason, comment, reply in rows:
        db.save_reply(cid, "vid1", comment, reply, status, reason)
    # c8 ko 2 din purana banao — --today me nahi aana chahiye
    db._db().execute(
        "UPDATE replies SET created_at = datetime('now', '-2 days') WHERE comment_id = ?",
        ("c8",),
    )
    db._db().commit()


def main():
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if not ok else ""))

    # --- 1) Empty db par --stats crash nahi kare ---
    _fresh_db("ytbot_review_empty.db")
    out = _run("--stats")
    check("empty db --stats", "Total rows: 0" in out and "koi row nahi" in out)

    # --- 2) Seed + stats counts ---
    _fresh_db()
    _seed()
    total, by_status, by_reason, today = db.reply_stats()
    check("stats total = 8", total == 8, f"got {total}")
    check(
        "stats status counts",
        dict(by_status) == {"draft": 4, "posted": 2, "skipped": 1, "failed": 1},
        str(dict(by_status)),
    )
    check("stats aaj = 7 (purana draft nahi)", sum(n for _, n in today) == 7, str(today))

    out = _run("--stats")
    check("--stats output", "Total rows: 8" in out and "Aaj (" in out, out[:120])

    # --- 3) --today sirf aaj ki rows ---
    out = _run("--today")
    check("--today rows = 7", out.rstrip().endswith("7 rows"), out.strip().splitlines()[-1])
    check("--today me purana draft nahi", "Bahut lamba comment" not in out)

    # --- 4) --drafts poora text ---
    out = _run("--drafts")
    check("--drafts rows = 4", out.rstrip().endswith("4 rows (sirf draft, full text)"))
    check("--drafts me poora long comment", LONG_COMMENT in out)

    # --- 5) --drafts --today = 3 (purana draft chhod kar) ---
    out = _run("--drafts", "--today")
    check("--drafts --today rows = 3", out.rstrip().endswith("3 rows (sirf draft, full text)"))

    # --- 6) normal table ---
    out = _run()
    check("normal table rows = 8", out.rstrip().endswith("8 rows"))

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nReview: {passed}/{len(checks)} PASS")

    lines = "\n".join(
        f"| {name} | {'PASS' if ok else 'FAIL'} | {detail or '-'} |"
        for name, ok, detail in checks
    )
    report_utils.write_section(
        "STEP6",
        "## Step 6 — Review stats (`review.py --stats` / `--today`)\n\n"
        f"- Result: **{passed}/{len(checks)} PASS** (temp db, koi network call nahi)\n"
        "- `--stats`: total + status counts + reason counts + aaj ka hisaab\n"
        "- `--today`: sirf aaj (local date) ki rows; `--drafts --today` dono filter\n\n"
        "| Check | Result | Detail |\n|---|---|---|\n" + lines,
    )
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
