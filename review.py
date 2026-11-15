# review.py — db ke recent replies ka table (draft review ke liye)
# Chalao:
#   python review.py            -> last 20 rows (kisi bhi status ki)
#   python review.py --drafts   -> sirf draft rows (poora comment + reply)
#   python review.py --today    -> sirf aaj ki rows
#   python review.py --stats    -> total + status/reason counts + aaj ka hisaab
import sys  # argv + console encoding ke liye
from datetime import datetime  # --stats me aaj ki date dikhane ke liye

# Windows console cp1252 hai — emoji wale comments bina crash ke chhapein
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import db  # saara database code db.py me (yahan koi query nahi)


def _cut(s, n):
    # Ek line me + n char tak; zyada lamba ho to kaato (…) — table ki alignment na toote
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _print_stats():
    total, by_status, by_reason, today = db.reply_stats()
    print("=== REPLY STATS ===")
    print(f"Total rows: {total}\n")

    print("Status:")
    for name, n in by_status:
        print(f"  {name:10} {n}")
    if not by_status:
        print("  (khali)")

    print("\nReason:")
    for name, n in by_reason:
        print(f"  {(name or '(khali)'):24} {n}")
    if not by_reason:
        print("  (khali)")

    print(f"\nAaj ({datetime.now().strftime('%Y-%m-%d')}):")
    if not today:
        print("  koi row nahi")
    for name, n in today:
        print(f"  {name:10} {n}")


def _print_owner():
    """needs_owner / asks_if_bot rows — owner khud jawab de (comment + video + link)."""
    rows = db.owner_rows()
    if not rows:
        print("Koi 'needs_owner' ya 'asks_if_bot' row nahi mila.")
        return
    for comment_id, video_id, reason, comment, created_at, title in rows:
        link = f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"
        print(f"--- {reason} | {created_at}")
        print(f"VIDEO  : {title or '(video title nahi hai)'}")
        print(f"COMMENT: {comment or ''}")
        print(f"LINK   : {link}")
        print()
    print(f"{len(rows)} rows (owner ko khud jawab dena hai)")


def main():
    args = sys.argv[1:]
    if "--stats" in args:  # stats apne aap me poora output hai
        _print_stats()
        return
    if "--owner" in args:  # owner ke jawab wale comments
        _print_owner()
        return

    drafts_only = "--drafts" in args  # sirf draft rows dikhani hain
    today_only = "--today" in args    # sirf aaj ki rows
    rows = db.recent_replies(
        limit=20,
        status="draft" if drafts_only else None,
        today_only=today_only,
    )
    if not rows:
        print("Koi row nahi mila.")
        return

    # --- Drafts: comment + reply POORA text (truncate BILKUL nahi) ---
    if drafts_only:
        for i, (created_at, _status, reason, comment, reply) in enumerate(rows, 1):
            print(f"--- Draft {i} | {created_at} | reason={reason}")
            print(f"COMMENT: {comment or ''}")  # poora comment, jaisa hai waisa
            print(f"REPLY  : {reply or ''}")  # poora reply bhi
            print()
        print(f"{len(rows)} rows (sirf draft, full text)")
        return

    # --- Normal table: last 20 rows, columns chhote rakhe hain isliye cut hota hai ---
    # Column widths: time 19 | status 8 | reason 16 | comment 60 | reply (baaki)
    print(f"{'TIME':19}  {'STATUS':8}  {'REASON':16}  {'COMMENT (60)':60}  REPLY (80)")
    print("-" * 145)
    for created_at, status, reason, comment, reply in rows:
        print(
            f"{created_at:19}  {status:8}  {_cut(reason, 16):16}  "
            f"{_cut(comment, 60):60}  {_cut(reply, 80)}"
        )
    print(f"\n{len(rows)} rows")


if __name__ == "__main__":
    main()
