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
    """Sirf FINAL statuses = done (posted/skipped/failed). Draft row = NOT done.

    Draft rows har run me dobara process hoti hain — save_reply ka INSERT OR REPLACE
    usi comment_id ki row ko update karta hai, isliye duplicate row NAHI banti.
    """
    cur = _db().execute(
        "SELECT 1 FROM replies WHERE comment_id = ? "
        "AND status IN ('posted', 'skipped', 'failed')",
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


def emoji_replies_today():
    # Aaj kitne emoji-canned replies ban chuke (draft ya posted) — daily cap isi se
    # created_at UTC hai (SQLite datetime('now')), isliye date('now') se sahi match hoga
    row = _db().execute(
        "SELECT COUNT(*) FROM replies "
        "WHERE reason = 'emoji' AND status IN ('draft', 'posted') "
        "AND date(created_at) = date('now')"
    ).fetchone()
    return row[0]


def recent_replies(limit=20, status=None):
    # review.py ke liye: latest rows (status diya ho to sirf wahi, jaise "draft")
    # ORDER BY created_at DESC + rowid — same second ki rows ka order bhi stable rahe
    if status:
        cur = _db().execute(
            "SELECT created_at, status, reason, comment, reply FROM replies "
            "WHERE status = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (status, limit),
        )
    else:
        cur = _db().execute(
            "SELECT created_at, status, reason, comment, reply FROM replies "
            "ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (limit,),
        )
    return cur.fetchall()


if __name__ == "__main__":
    # Chhota self-check: draft = NOT done, posted = done, row ek hi rehti hai
    init_db()
    save_reply("smoke_test", "vid1", "hi", "hello", "draft", "selfcheck")
    assert not already_done("smoke_test"), "draft row ko done nahi hona chahiye"
    save_reply("smoke_test", "vid1", "hi", "hello2", "posted", "selfcheck")
    assert already_done("smoke_test"), "posted row done honi chahiye"
    # Dobara save par PURANI row hi update honi chahiye — duplicate row nahi
    n = _db().execute(
        "SELECT COUNT(*) FROM replies WHERE comment_id = 'smoke_test'"
    ).fetchone()[0]
    assert n == 1, "duplicate row ban gayi!"
    assert not already_done("no_such_comment"), "false positive"
    _db().execute("DELETE FROM replies WHERE comment_id = 'smoke_test'")
    _db().commit()
    print("db.py self-check PASS")
