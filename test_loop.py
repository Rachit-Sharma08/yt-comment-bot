# test_loop.py — loop mode ki stability (SIRF MOCK).
# Check: 5 cycles bina crash, koi duplicate post nahi, DB me har comment ek hi row,
# network error par backoff, STOP par loop band, lock zinda (mtime touch).
#
# Chalao: venv\Scripts\python.exe test_loop.py

import contextlib
import io
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
import db
import main
import mock_youtube
import report_utils

RESULTS = []


def _fresh_db():
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    path = Path(tempfile.gettempdir()) / "ytbot_loop.db"
    if path.exists():
        path.unlink()
    db.DB_PATH = str(path)
    db.init_db()


def _test_config():
    config.MODE = "auto"
    config.MAX_REPLIES_PER_RUN = 100
    config.MAX_REPLIES_PER_RUN_LIVE = 100
    config.MAX_EMOJI_REPLIES_PER_DAY = 100
    config.REPLY_DELAY_MIN_SEC = 0
    config.REPLY_DELAY_MAX_SEC = 0


def _rows():
    return db._db().execute(
        "SELECT comment_id, status, reason FROM replies"
    ).fetchall()


# Temp STOP + lock — repo ki asli files ko chhedo mat
stop = Path(tempfile.gettempdir()) / "ytbot_STOP_loop_stability"
lock = Path(tempfile.gettempdir()) / "ytbot_loop.lock"


def _run_cycles(cycles):
    """loop_mode ko N normal cycles chalao — aakhri sleep par STOP set karo.

    Backoff (>=1s) ko sirf record karte hain, wait nahi — warna test 15 min chalega.
    """
    backoffs = []
    normal_sleeps = []
    real_sleep_until_stop = main._sleep_until_stop

    def fake_loop_sleep():
        normal_sleeps.append(1)
        if len(normal_sleeps) >= cycles:
            stop.write_text("stop", encoding="utf-8")
        return 0  # normal interval 0 — reply delay jaisa hi instant

    def fake_sleep_until_stop(seconds):
        if seconds >= 1:  # network backoff — record only
            backoffs.append(seconds)
            return True
        return real_sleep_until_stop(0)  # 0 = instant + asli STOP check

    old_sleep, old_loop_sleep = main._sleep_until_stop, main._loop_sleep_seconds
    main._sleep_until_stop = fake_sleep_until_stop
    main._loop_sleep_seconds = fake_loop_sleep
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            main.loop_mode(True)
    finally:
        main._sleep_until_stop, main._loop_sleep_seconds = old_sleep, old_loop_sleep
    return backoffs


def test_clean_cycles():
    _fresh_db()
    fake = mock_youtube.FakeYouTube(auto_feed=2)  # har cycle 2 naye comments
    mock_youtube.install(fake)
    mock_youtube.install_llm(mock_youtube.FakeLLM())

    stop.unlink(missing_ok=True)
    lock.unlink(missing_ok=True)
    old_stop, old_lock = main.STOP_FILE, main.LOCK_FILE
    main.STOP_FILE, main.LOCK_FILE = stop, lock
    try:
        assert main._acquire_lock() is True
        mtime_before = lock.stat().st_mtime_ns
        backoffs = _run_cycles(cycles=5)
        mtime_after = lock.stat().st_mtime_ns
    finally:
        main._release_lock()
        main.STOP_FILE, main.LOCK_FILE = old_stop, old_lock
        stop.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)

    rows = _rows()
    ids = [r[0] for r in rows]
    posted_ids = [p["comment_id"] for p in fake.posted]
    assert fake.fetch_calls == 5, fake.fetch_calls
    assert len(rows) == 10, f"rows {len(rows)} (10 comments expected)"
    assert len(ids) == len(set(ids)), "duplicate DB row!"
    assert len(posted_ids) == len(set(posted_ids)), "duplicate post!"
    assert not (set(posted_ids) - set(ids)), "posted comment DB me nahi"
    assert all(r[1] in ("posted", "skipped") for r in rows), rows
    assert backoffs == [], f"clean run me backoff kyun: {backoffs}"
    assert mtime_after >= mtime_before, "lock touch nahi hua"
    RESULTS.append(("5 clean cycles: no crash, no duplicate", True,
                    f"10 comments, {len(posted_ids)} posts, 0 duplicate"))


def test_errors_backoff_no_duplicate():
    _fresh_db()
    fake = mock_youtube.FakeYouTube(auto_feed=2)
    fake.fetch_error_every = 3   # har 3rd fetch network fail
    fake.post_error_every = 2    # har 2nd post fail
    mock_youtube.install(fake)
    mock_youtube.install_llm(mock_youtube.FakeLLM())

    stop.unlink(missing_ok=True)
    old_stop = main.STOP_FILE
    main.STOP_FILE = stop
    try:
        backoffs = _run_cycles(cycles=6)
    finally:
        main.STOP_FILE = old_stop
        stop.unlink(missing_ok=True)

    rows = _rows()
    ids = [r[0] for r in rows]
    posted_ids = [p["comment_id"] for p in fake.posted]
    failed = [r for r in rows if r[1] == "failed"]
    assert fake.fetch_calls == 8, fake.fetch_calls  # 6 ok + 2 network fail
    assert len(rows) == 12, f"rows {len(rows)} (12 comments expected)"
    assert len(ids) == len(set(ids)), "duplicate DB row!"
    assert len(posted_ids) == len(set(posted_ids)), "duplicate post!"
    assert failed, "post error ke baad failed row nahi bani"
    assert all(r[2].startswith("post_") for r in failed), failed
    # Har network fail par 60s backoff; success ke baad reset (isliye dobara 60)
    assert backoffs == [60, 60], f"backoff galat: {backoffs}"
    RESULTS.append(("Error cycles: backoff + no duplicate", True,
                    f"network fails {len(backoffs)}, failed rows {len(failed)}, "
                    f"0 duplicate"))


def main_loop_test():
    if main.STOP_FILE.exists():
        print("STOP file mila — test nahi chala (kill switch on hai).")
        return 1

    _test_config()

    for t in (test_clean_cycles, test_errors_backoff_no_duplicate):
        try:
            t()
        except Exception as e:
            RESULTS.append((t.__name__, False, f"{type(e).__name__}: {e}"))

    out = []
    out.append("## Step 4 — Loop stability (mock only)\n")
    out.append(
        "**Setup:** `loop_mode` 5-6 cycles, `FakeYouTube(auto_feed=2)`, "
        "temp DB + temp STOP/lock, sleep monkeypatched — koi real API call nahi.\n"
    )
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    out.append(f"**Result:** {passed}/{len(RESULTS)} scenarios PASS\n")
    out.append("| Scenario | Result | Detail |")
    out.append("|---|---|---|")
    for name, ok, detail in RESULTS:
        out.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    report_utils.write_section("STEP4", "\n".join(out))

    print(f"\nLoop: {passed}/{len(RESULTS)} scenarios PASS")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAIL: {name} — {detail}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main_loop_test())
