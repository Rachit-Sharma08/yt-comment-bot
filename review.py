# review.py — db ke recent replies ka table (draft review ke liye)
# Chalao:
#   python review.py           -> last 20 rows (kisi bhi status ki)
#   python review.py --drafts  -> sirf draft rows
import sys  # argv + console encoding ke liye

# Windows console cp1252 hai — emoji wale comments bina crash ke chhapein
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import db  # saara database code db.py me (yahan koi query nahi)


def _cut(s, n):
    # Ek line me + n char tak; zyada lamba ho to kaato (…) — table ki alignment na toote
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    drafts_only = "--drafts" in sys.argv[1:]  # sirf draft rows dikhani hain
    rows = db.recent_replies(limit=20, status="draft" if drafts_only else None)
    if not rows:
        print("Koi row nahi mila.")
        return

    # Column widths: time 19 | status 8 | reason 16 | comment 60 | reply (baaki)
    print(f"{'TIME':19}  {'STATUS':8}  {'REASON':16}  {'COMMENT (60)':60}  REPLY (80)")
    print("-" * 145)
    for created_at, status, reason, comment, reply in rows:
        print(
            f"{created_at:19}  {status:8}  {_cut(reason, 16):16}  "
            f"{_cut(comment, 60):60}  {_cut(reply, 80)}"
        )
    print(f"\n{len(rows)} rows" + (" (sirf draft)" if drafts_only else ""))


if __name__ == "__main__":
    main()
