# test_runner.py — Step 7: run_bot.bat ka Windows runner test (koi network nahi)
# Test hook: BOT_TEST_EXIT env var se bot ka exit code simulate hota hai.
# Chalao: venv\Scripts\python.exe test_runner.py

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import report_utils

ROOT = Path(__file__).parent
RESTART_MSG = "dobara chalaunga"


def _run(bat, env_extra=None, cwd=None, timeout=120):
    """cmd se .bat chalao — (returncode, output)."""
    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.run(
        ["cmd", "/c", str(bat)],
        env=env,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if not ok else ""))

    run_bat = ROOT / "run_bot.bat"
    stop_bat = ROOT / "stop_bot.bat"
    resume_bat = ROOT / "resume_bot.bat"

    # --- 0) files maujood hain ---
    check("run_bot.bat / stop_bot.bat / resume_bot.bat exist",
          run_bat.exists() and stop_bat.exists() and resume_bat.exists())

    # --- 1) Token expire (exit 3) = NO restart, exit code 3 ---
    code, out = _run(run_bat, {"BOT_TEST_EXIT": "3"})
    check("exit 3 -> returncode 3", code == 3, f"got {code}")
    check("exit 3 -> token message", "Token expire ho gaya" in out, out[:160])
    check("exit 3 -> koi restart nahi", RESTART_MSG not in out, out[:160])

    # --- 2) Galat flag (exit 2) = restart nahi ---
    code, out = _run(run_bat, {"BOT_TEST_EXIT": "2"})
    check("exit 2 -> returncode 2 + no restart",
          code == 2 and RESTART_MSG not in out, f"code={code}")

    # --- 3) Normal exit 0 ---
    code, out = _run(run_bat, {"BOT_TEST_EXIT": "0"})
    check("exit 0 -> returncode 0", code == 0, f"got {code}")

    # --- 4) Baaki error (exit 1) -> ek restart, phir ruk ---
    code, out = _run(run_bat, {"BOT_TEST_EXIT": "1", "BOT_MAX_RESTARTS": "1",
                               "BOT_RESTART_DELAY": "1"})
    check("exit 1 -> restart hua", RESTART_MSG in out, out[:200])
    check("exit 1 -> limit ke baad ruka + code 1",
          "ruk raha hoon" in out and code == 1, f"code={code}")

    # --- 5) Temp copy: venv na ho + STOP file = kill switch ---
    tmp = Path(tempfile.mkdtemp(prefix="ytbot_runner_"))
    try:
        for b in (run_bat, stop_bat, resume_bat):
            shutil.copy(b, tmp / b.name)

        code, out = _run(tmp / "run_bot.bat", {}, cwd=tmp)
        check("venv na ho -> returncode 2 + message",
              code == 2 and "venv" in out.lower(), f"code={code} out={out[:120]}")

        code, out = _run(tmp / "stop_bot.bat", {}, cwd=tmp)
        check("stop_bot.bat -> STOP file bani",
              code == 0 and (tmp / "STOP").exists(), out[:120])

        code, out = _run(tmp / "run_bot.bat", {}, cwd=tmp)
        check("STOP file -> bot nahi chala (code 0)",
              code == 0 and "STOP file mila" in out, f"code={code} out={out[:120]}")

        code, out = _run(tmp / "resume_bot.bat", {}, cwd=tmp)
        check("resume_bot.bat -> STOP file hata di",
              code == 0 and not (tmp / "STOP").exists(), out[:120])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nRunner: {passed}/{len(checks)} PASS")

    lines = "\n".join(
        f"| {name} | {'PASS' if ok else 'FAIL'} | {detail or '-'} |"
        for name, ok, detail in checks
    )
    report_utils.write_section(
        "STEP7",
        "## Step 7 — Windows runner (`run_bot.bat`) + autostart docs\n\n"
        f"- Result: **{passed}/{len(checks)} PASS** (koi network call nahi, sirf .bat logic)\n"
        "- `run_bot.bat` -> `main.py --loop`; `--live` passthrough se aata hai\n"
        "- Exit 3 (token expire / invalid_grant) par **restart nahi** hota\n"
        "- Exit 2 (galat flag) par bhi restart nahi; baaki error par 60s gap ke saath restart\n"
        "- Kill switch: `stop_bot.bat` (STOP file) / `resume_bot.bat` (delete)\n"
        "- Task Scheduler me kuch bhi register nahi kiya gaya — steps sirf "
        "`WINDOWS_RUN.md` me documented hain\n\n"
        "| Check | Result | Detail |\n|---|---|---|\n" + lines,
    )
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
