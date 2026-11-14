# report_utils.py — OVERNIGHT_REPORT.md ko section-wise likho (marker ke andar).
# Har script apna section replace karta hai — rerun par duplicate section nahi banta.

import platform
from datetime import datetime
from pathlib import Path

REPORT = Path(__file__).parent / "OVERNIGHT_REPORT.md"


def init_report():
    # Report ek hi baar banao — baaki scripts sections jodti hain
    if REPORT.exists():
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    REPORT.write_text(
        "# Overnight Test Report — YouTube Comment Bot\n\n"
        f"- Date: {now}\n"
        f"- Machine: {platform.system()} {platform.release()}, "
        f"Python {platform.python_version()}\n"
        "- Sab tests mock/controlled hain: **real YouTube API call nahi hui, "
        "koi POST nahi hua**, secrets (.env/token.json/client_secret.json) "
        "nahi khole gaye.\n",
        encoding="utf-8",
    )


def write_section(name, text):
    init_report()
    start = f"<!-- {name}:START -->"
    end = f"<!-- {name}:END -->"
    block = f"{start}\n{text.strip()}\n{end}"

    content = REPORT.read_text(encoding="utf-8")
    if start in content and end in content:
        pre = content.split(start)[0]
        post = content.split(end, 1)[1]
        content = pre + block + post
    else:
        content = content.rstrip() + "\n\n" + block + "\n"
    REPORT.write_text(content, encoding="utf-8")
