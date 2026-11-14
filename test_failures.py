# test_failures.py — failure handling ka test (SIRF MOCK, koi real API call nahi).
# Har scenario alag temp DB par chalta hai — bot.db ko chhedo mat.
#
# Chalao: venv\Scripts\python.exe test_failures.py

import contextlib
import io
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest import mock

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
import db
import main
import mock_youtube
import report_utils
import youtube
from google.auth.exceptions import RefreshError

RESULTS = []  # [(scenario, ok, detail)]


def _fresh_db():
    # Har scenario apni alag db — pichle test ke rows mix na hon
    if db._conn is not None:
        db._conn.close()
    db._conn = None
    path = Path(tempfile.gettempdir()) / "ytbot_failures.db"
    if path.exists():
        path.unlink()
    db.DB_PATH = str(path)
    db.init_db()


def _test_config():
    # Test-only runtime settings — config.py ke defaults nahi badalte
    config.MODE = "auto"
    config.MAX_REPLIES_PER_RUN = 100
    config.MAX_REPLIES_PER_RUN_LIVE = 100
    config.REPLY_DELAY_MIN_SEC = 0
    config.REPLY_DELAY_MAX_SEC = 0


def _row(comment_id):
    row = db._db().execute(
        "SELECT status, reason, reply FROM replies WHERE comment_id = ?",
        (comment_id,),
    ).fetchone()
    if not row:
        return None
    return {"status": row[0], "reason": row[1], "reply": row[2]}


def _record(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


# --- Fake 403 quotaExceeded (googleapiclient HttpError jaisa shape) ---
class _Resp403:
    status = 403


class _Quota403(Exception):
    resp = _Resp403()
    content = b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}'


class _Rate403(Exception):
    resp = _Resp403()
    content = b'{"error":{"errors":[{"reason":"rateLimitExceeded"}]}}'


def test_llm_failure_retries_next_run():
    _fresh_db()
    fake = mock_youtube.FakeYouTube()
    fake.add_comment("Bhai ye camera kaunsa hai?", comment_id="f-llm-1")
    mock_youtube.install(fake)
    # Pehla reply call fail (429 jaisa), doosra success
    mock_youtube.install_llm(mock_youtube.FakeLLM(fail_first=1))

    main.run(live=True)
    row = _row("f-llm-1")
    assert row and row["status"] == "failed" and row["reason"] == "llm_fail", row
    assert not db.already_done("f-llm-1"), "llm_fail retry hona chahiye"

    main.run(live=True)  # agla run — retry
    row2 = _row("f-llm-1")
    assert row2 and row2["status"] == "posted", row2
    assert len(fake.posted) == 1, fake.posted
    _record("LLM 429 -> failed, agle run me retry", True,
            "pehla run failed/llm_fail, doosra run posted")


def test_post_failure_not_posted_and_no_duplicate():
    _fresh_db()
    fake = mock_youtube.FakeYouTube()
    fake.add_comment("Nice video bro", comment_id="f-post-1")
    mock_youtube.install(fake)
    mock_youtube.install_llm(mock_youtube.FakeLLM())

    fake.post_error = RuntimeError("boom")
    main.run(live=True)
    row = _row("f-post-1")
    assert row and row["status"] == "failed" and row["reason"] == "post_error", row
    assert fake.posted == [], "post fail par posted record nahi hona chahiye"
    assert db.already_done("f-post-1"), "post fail dobara nahi jaana chahiye"

    fake.post_error = None
    main.run(live=True)  # dobara fetch — ye comment skip hona chahiye
    assert fake.posted == [], "duplicate post ho gaya!"
    assert _row("f-post-1")["status"] == "failed", "row badal gayi"
    _record("Post fail -> failed (posted nahi) + no duplicate", True,
            "row failed/post_error, agle run me skip")


def test_quota_403_on_fetch_skips_day():
    _fresh_db()
    fake = mock_youtube.FakeYouTube()

    def _boom(max_results=50):
        raise _Quota403("quota")

    fake.fetch_new_comments = _boom
    mock_youtube.install(fake)

    main.run(live=True)
    assert db.quota_used_today() == config.QUOTA_LIMIT, db.quota_used_today()
    _record("Fetch par 403 quotaExceeded -> aaj ke baaki runs skip", True,
            f"quota {db.quota_used_today()}/{config.QUOTA_LIMIT}")


def test_quota_403_on_post_stops_run():
    _fresh_db()
    fake = mock_youtube.FakeYouTube()
    fake.add_comment("Nice video bro", comment_id="f-q1")
    fake.add_comment("Great video", comment_id="f-q2")
    mock_youtube.install(fake)
    mock_youtube.install_llm(mock_youtube.FakeLLM())
    fake.post_error = _Quota403("quota")

    main.run(live=True)
    row = _row("f-q1")
    assert row and row["status"] == "failed" and row["reason"] == "post_quota", row
    assert _row("f-q2") is None, "quota ke baad run nahi ruka"
    assert db.quota_used_today() == config.QUOTA_LIMIT, db.quota_used_today()
    assert fake.posted == []
    _record("Post par 403 quotaExceeded -> run rukta hai + day skip", True,
            "q1 failed/post_quota, q2 process nahi hua")


def test_local_quota_error_skips_day():
    _fresh_db()
    fake = mock_youtube.FakeYouTube()

    def _boom(max_results=50):
        raise youtube.QuotaExceededError("Quota khatam: local limit")

    fake.fetch_new_comments = _boom
    mock_youtube.install(fake)

    main.run(live=True)
    assert db.quota_used_today() == config.QUOTA_LIMIT, db.quota_used_today()
    _record("Local QUOTA_LIMIT -> day skip", True,
            f"quota {db.quota_used_today()}/{config.QUOTA_LIMIT}")


def test_quota_detector_and_backoff():
    assert youtube.quota_exceeded(_Quota403("q"))
    assert not youtube.quota_exceeded(_Rate403("r")), "rate limit ko day-skip na samjho"
    assert not youtube.quota_exceeded(RuntimeError("x"))
    assert main._backoff_seconds(0) == 60
    assert main._backoff_seconds(60) == 120
    assert main._backoff_seconds(480) == 900, "15 min cap toota"
    assert main._backoff_seconds(900) == 900
    assert main._is_network_error(ConnectionError("x"))
    assert main._is_network_error(TimeoutError("x"))
    assert not main._is_network_error(RuntimeError("x"))
    import requests
    assert main._is_network_error(requests.exceptions.ConnectionError())
    assert main._is_network_error(requests.exceptions.Timeout())
    _record("Quota detector + network backoff (60s..15min)", True,
            "403 quotaExceeded alag, rateLimitExceeded alag")


def test_stop_mid_sleep():
    tmp = Path(tempfile.gettempdir()) / "ytbot_STOP_sleep_test"
    tmp.unlink(missing_ok=True)
    orig = main.STOP_FILE
    main.STOP_FILE = tmp
    try:
        timer = threading.Timer(0.3, lambda: tmp.write_text("stop", encoding="utf-8"))
        timer.start()
        t0 = time.time()
        ok = main._sleep_until_stop(10)  # beech me STOP aayega
        elapsed = time.time() - t0
        timer.cancel()
        assert ok is False, "STOP ke baad bhi sleep chalti rahi"
        assert elapsed < 3, f"STOP par turant nahi ruka ({elapsed:.1f}s)"
    finally:
        main.STOP_FILE = orig
        tmp.unlink(missing_ok=True)
    _record("STOP mid-sleep -> turant loop band", True,
            f"{elapsed:.1f}s me ruk gaya (10s sleep)")


def test_loop_stop_and_quota_skip():
    tmp = Path(tempfile.gettempdir()) / "ytbot_STOP_loop_test"
    tmp.unlink(missing_ok=True)
    orig_stop = main.STOP_FILE
    main.STOP_FILE = tmp
    calls = []
    try:
        # 1) STOP file pehle se hai -> loop turant band, run kabhi nahi
        tmp.write_text("stop", encoding="utf-8")
        with mock.patch.object(main, "run", side_effect=AssertionError("run chala!")):
            main.loop_mode(False)  # STOP mila to turant return
        tmp.unlink(missing_ok=True)

        # 2) Quota khatam -> run skip, pehli sleep par STOP jaisa -> loop band
        _fresh_db()
        db.mark_quota_exhausted(config.QUOTA_LIMIT)
        with mock.patch.object(main, "run", side_effect=lambda live: calls.append(live)), \
             mock.patch.object(main, "_sleep_until_stop", return_value=False):
            main.loop_mode(False)
        assert calls == [], "quota khatam hone par run chala"
    finally:
        main.STOP_FILE = orig_stop
        tmp.unlink(missing_ok=True)
    _record("Loop: STOP par band + quota par run skip", True,
            "STOP -> exit, quota -> run 0 baar")


def test_lock_single_instance():
    tmp = Path(tempfile.gettempdir()) / "ytbot_test.lock"
    tmp.unlink(missing_ok=True)
    orig = main.LOCK_FILE
    main.LOCK_FILE = tmp
    try:
        assert main._acquire_lock() is True
        assert main._acquire_lock() is False, "doosra instance chal gaya!"
        main._release_lock()
        # Stale lock (30 min purana) -> kabza le lo
        tmp.write_text("999", encoding="utf-8")
        old = time.time() - (main.LOCK_STALE_SEC + 60)
        os.utime(tmp, (old, old))
        assert main._acquire_lock() is True, "stale lock nahi hata"
        main._release_lock()
    finally:
        main.LOCK_FILE = orig
        tmp.unlink(missing_ok=True)
    _record("bot.lock: doosra instance band, stale lock clear", True,
            "second instance False, stale lock acquire True")


def test_invalid_grant_token():
    class _FakeCreds:
        valid = False
        refresh_token = "fake-refresh"

        def refresh(self, req):
            raise RefreshError("invalid_grant: Token has been expired or revoked.")

    with mock.patch.object(youtube.os.path, "exists", return_value=True), \
         mock.patch.object(youtube.Credentials, "from_authorized_user_file",
                           return_value=_FakeCreds()):
        try:
            youtube.get_credentials()
            ok = False
        except youtube.TokenExpiredError:
            ok = True
    assert ok, "invalid_grant par TokenExpiredError nahi aaya"
    _record("invalid_grant -> TokenExpiredError", True,
            "token.json ko chheda nahi (mock)")


def test_token_exit_code_3():
    out = io.StringIO()
    code = None
    with mock.patch.object(main, "_acquire_lock", return_value=True), \
         mock.patch.object(main, "_release_lock"), \
         mock.patch.object(main, "run", side_effect=youtube.TokenExpiredError()), \
         mock.patch.object(sys, "argv", ["main.py", "--once"]):
        try:
            with contextlib.redirect_stdout(out):
                main.main()
        except SystemExit as e:
            code = e.code
    assert code == 3, f"exit code {code} (3 chahiye)"
    assert main.TOKEN_EXPIRED_MSG in out.getvalue(), out.getvalue()
    _record("Token expire -> exit code 3 + exact message", True,
            main.TOKEN_EXPIRED_MSG)


def main_failures():
    if main.STOP_FILE.exists():
        print("STOP file mila — test nahi chala (kill switch on hai).")
        return 1

    _test_config()

    tests = [
        test_llm_failure_retries_next_run,
        test_post_failure_not_posted_and_no_duplicate,
        test_quota_403_on_fetch_skips_day,
        test_quota_403_on_post_stops_run,
        test_local_quota_error_skips_day,
        test_quota_detector_and_backoff,
        test_stop_mid_sleep,
        test_loop_stop_and_quota_skip,
        test_lock_single_instance,
        test_invalid_grant_token,
        test_token_exit_code_3,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            _record(t.__name__, False, f"{type(e).__name__}: {e}")

    # --- Report section ---
    out = []
    out.append("## Step 3 — Failure handling (mock only)\n")
    out.append(
        "**Setup:** har scenario alag temp DB (`ytbot_failures.db`), "
        "`FakeYouTube` + `FakeLLM`, koi real YouTube/LLM call nahi, "
        "token.json ko chheda nahi (mock).\n"
    )
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    out.append(f"**Result:** {passed}/{len(RESULTS)} scenarios PASS\n")
    out.append("| Scenario | Result | Detail |")
    out.append("|---|---|---|")
    for name, ok, detail in RESULTS:
        out.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    report_utils.write_section("STEP3", "\n".join(out))

    print(f"\nFailures: {passed}/{len(RESULTS)} scenarios PASS")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAIL: {name} — {detail}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main_failures())
