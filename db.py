# db.py — saara database code sirf yahin (SQLite, bot.db)
# Ye file baad me Supabase par shift ho sake — isliye har query yahin se hokar jaati hai
# bot.db .gitignore me hai — kabhi commit nahi hogi

import sqlite3  # Python ka built-in SQLite driver — koi extra package nahi
from datetime import datetime  # aaj ki date (quota ke liye) nikalne ke liye

DB_PATH = "bot.db"  # database file isi folder me banegi

# Ek hi connection poori run ke liye — simple aur fast (bot single-threaded hai)
_conn = None


def _db():
    # Pehli baar connection banao, uske baad wahi reuse karo
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
    return _conn


def init_db():
    # Teeno tables banao — pehle se bani hain to kuch nahi hota (IF NOT EXISTS)
    _db().executescript(
        """
        CREATE TABLE IF NOT EXISTS replies (
            comment_id TEXT PRIMARY KEY,  -- YouTube comment id = duplicate check isi se
            video_id   TEXT,             -- kaun si video par comment aaya
            comment    TEXT,             -- original comment text
            reply      TEXT,             -- bot ka reply (skipped/failed par khali)
            status     TEXT,             -- draft / posted / skipped / failed
            reason     TEXT,             -- skip ya failure ka chhota reason
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS videos (
            video_id    TEXT PRIMARY KEY,
            title       TEXT,
            description TEXT,
            fetched_at  TEXT DEFAULT (datetime('now'))  -- kab cache kiya (refresh ke liye)
        );
        CREATE TABLE IF NOT EXISTS quota (
            date       TEXT PRIMARY KEY,  -- YYYY-MM-DD (roz ka hisaab)
            units_used INTEGER            -- us din kitne units kharch hue
        );
        """
    )
    _db().commit()


def already_done(comment_id):
    """Sirf FINAL statuses = done. Draft = NOT done.

    - posted / skipped  = hamesha done
    - failed + post_*   = done (post ho chuka ya ho sakta tha — dobara bhejna = duplicate)
    - failed + baaki    = NOT done (LLM 429/network fail — agle run me retry hona chahiye)

    Draft rows har run me dobara process hoti hain — save_reply ka INSERT OR REPLACE
    usi comment_id ki row ko update karta hai, isliye duplicate row NAHI banti.
    """
    cur = _db().execute(
        "SELECT 1 FROM replies WHERE comment_id = ? "
        "AND (status IN ('posted', 'skipped') "
        "     OR (status = 'failed' AND reason LIKE 'post_%'))",
        (comment_id,),
    )
    return cur.fetchone() is not None


def save_reply(comment_id, video_id, comment, reply, status, reason=""):
    # Ek comment = ek row — dobara save par purani row hi update ho jaati hai
    _db().execute(
        "INSERT OR REPLACE INTO replies "
        "(comment_id, video_id, comment, reply, status, reason) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (comment_id, video_id, comment, reply, status, reason),
    )
    _db().commit()


def get_video(video_id):
    # Cache hit ho to (title, description) warna None — API call yahin se bachti hai
    row = _db().execute(
        "SELECT title, description FROM videos WHERE video_id = ?", (video_id,)
    ).fetchone()
    return (row[0], row[1]) if row else None


def save_video(video_id, title, description):
    # Naya ya purana video — dono me fresh data isi se replace hoga
    _db().execute(
        "INSERT OR REPLACE INTO videos (video_id, title, description, fetched_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (video_id, title, description),
    )
    _db().commit()


def add_quota(units):
    # Aaj ke din ke units me jodo — pehli baar ho to nayi row bana do
    today = datetime.now().strftime("%Y-%m-%d")
    _db().execute(
        "INSERT INTO quota (date, units_used) VALUES (?, ?) "
        "ON CONFLICT(date) DO UPDATE SET units_used = units_used + excluded.units_used",
        (today, units),
    )
    _db().commit()


def quota_used_today():
    # Aaj kharche kitne hue — YouTube API limit check yahi se hota hai
    today = datetime.now().strftime("%Y-%m-%d")
    row = _db().execute(
        "SELECT units_used FROM quota WHERE date = ?", (today,)
    ).fetchone()
    return row[0] if row else 0


def mark_quota_exhausted(limit):
    """YouTube ne 403 quotaExceeded diya — aaj ke liye local counter limit par set.

    Iske baad loop ka quota check khud hi aaj ke baaki runs skip kar dega.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    _db().execute(
        "INSERT INTO quota (date, units_used) VALUES (?, ?) "
        "ON CONFLICT(date) DO UPDATE SET units_used = excluded.units_used",
        (today, limit),
    )
    _db().commit()


def emoji_replies_today():
    # Aaj kitne emoji-canned replies ban chuke (draft ya posted) — daily cap isi se
    # created_at UTC hai (SQLite datetime('now')), isliye date('now') se sahi match hoga
    row = _db().execute(
        "SELECT COUNT(*) FROM replies "
        "WHERE reason = 'emoji' AND status IN ('draft', 'posted') "
        "AND date(created_at) = date('now')"
    ).fetchone()
    return row[0]


def contact_replies_today():
    # Aaj kitne institute replies me phone/link gaya (draft ya posted) — daily cap
    # (reason='institute' wale replies hi count; digits-normalized 10+ = contact)
    import re  # sqlite me regexp nahi hai — Python me check kar lete hain
    rows = _db().execute(
        "SELECT reply FROM replies "
        "WHERE reason = 'institute' AND status IN ('draft', 'posted') "
        "AND date(created_at) = date('now')"
    ).fetchall()
    pat_url = re.compile(r"(?i)https?://|www\.|wa\.me")
    count = 0
    for (r,) in rows:
        if not r:
            continue
        digits = re.sub(r"\D", "", r)  # phone ko formatting se azad karke
        if pat_url.search(r) or len(digits) >= 10:
            count += 1
    return count


def link_replies_today():
    """Aaj kitne institute replies me zedking.in URL gaya (draft ya posted) — daily link cap."""
    import re
    rows = _db().execute(
        "SELECT reply FROM replies "
        "WHERE reason = 'institute' AND status IN ('draft', 'posted') "
        "AND date(created_at) = date('now')"
    ).fetchall()
    pat_url = re.compile(r"(?i)https?://[^\s/]*zedking\.in")
    count = 0
    for (r,) in rows:
        if r and pat_url.search(r):
            count += 1
    return count


def recent_replies(limit=20, status=None, today_only=False):
    # review.py ke liye: latest rows (status diya ho to sirf wahi, jaise "draft")
    # today_only = sirf aaj ki rows (local date — user ke din ke hisaab se)
    # ORDER BY created_at DESC + rowid — same second ki rows ka order bhi stable rahe
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    if today_only:
        where.append("date(created_at, 'localtime') = date('now', 'localtime')")
    sql = "SELECT created_at, status, reason, comment, reply FROM replies"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
    params.append(limit)
    return _db().execute(sql, params).fetchall()


def owner_rows(limit=50):
    """needs_owner / asks_if_bot rows — owner khud jawab de (comment + video + link)."""
    return _db().execute(
        "SELECT r.comment_id, r.video_id, r.reason, r.comment, r.created_at, "
        "COALESCE(v.title, '') "
        "FROM replies r LEFT JOIN videos v ON v.video_id = r.video_id "
        "WHERE r.reason IN ('needs_owner', 'asks_if_bot') "
        "ORDER BY r.created_at DESC, r.rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()


def reply_stats():
    """review.py --stats ke liye: (total, status-wise, reason-wise, aaj status-wise)."""
    conn = _db()
    total = conn.execute("SELECT COUNT(*) FROM replies").fetchone()[0]
    by_status = conn.execute(
        "SELECT COALESCE(status, '?'), COUNT(*) FROM replies "
        "GROUP BY status ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_reason = conn.execute(
        "SELECT COALESCE(reason, ''), COUNT(*) FROM replies "
        "GROUP BY reason ORDER BY COUNT(*) DESC"
    ).fetchall()
    today = conn.execute(
        "SELECT COALESCE(status, '?'), COUNT(*) FROM replies "
        "WHERE date(created_at, 'localtime') = date('now', 'localtime') "
        "GROUP BY status ORDER BY COUNT(*) DESC"
    ).fetchall()
    return total, by_status, by_reason, today


if __name__ == "__main__":
    # Chhota self-check: draft = NOT done, posted = done, row ek hi rehti hai
    init_db()
    save_reply("smoke_test", "vid1", "hi", "hello", "draft", "selfcheck")
    assert not already_done("smoke_test"), "draft row ko done nahi hona chahiye"
    save_reply("smoke_test", "vid1", "hi", "hello2", "posted", "selfcheck")
    assert already_done("smoke_test"), "posted row done honi chahiye"
    # LLM fail = retry hona chahiye (done NAHI)
    save_reply("smoke_test", "vid1", "hi", "", "failed", "llm_fail")
    assert not already_done("smoke_test"), "llm_fail ko retry hona chahiye"
    # Post fail = done (dobara post = duplicate)
    save_reply("smoke_test", "vid1", "hi", "hello", "failed", "post_error")
    assert already_done("smoke_test"), "post_error dobara nahi jaana chahiye"
    # Dobara save par PURANI row hi update honi chahiye — duplicate row nahi
    n = _db().execute(
        "SELECT COUNT(*) FROM replies WHERE comment_id = 'smoke_test'"
    ).fetchone()[0]
    assert n == 1, "duplicate row ban gayi!"
    assert not already_done("no_such_comment"), "false positive"
    # Quota marker: aaj ka counter limit par
    mark_quota_exhausted(8000)
    assert quota_used_today() == 8000, "quota marker kaam nahi kiya"
    _db().execute("DELETE FROM replies WHERE comment_id = 'smoke_test'")
    _db().execute("DELETE FROM quota")
    _db().commit()
    print("db.py self-check PASS")
