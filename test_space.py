# test_space.py — Problem 1: "youknow" / "theHaryanvi" jaise missing-space bug ka root cause
# Har stage ka repr() print karo: (a) LLM raw output, (b) make_reply return, (c) db value
# YouTube par KUCH post nahi hota — sirf LLM call + local db (test row delete ho jaati hai)

import sqlite3
import sys

# Windows console cp1252 hai — emoji wale comment bina crash ke chhapein
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai  # make_reply + _call_groq/_call_gemini isi me hain
import db  # video context cache (videos table) isi se milegi

# --- Stage (a) ke liye: requests.post par spy — model ka BINA-strip raw output pakdo ---
_raw = {}  # {"text": ...} — last API call ka raw content yahin aayega
_orig_post = ai.requests.post


def _spy_post(url, **kwargs):
    resp = _orig_post(url, **kwargs)
    try:
        if resp.ok:  # sirf success body me hi reply hota hai
            data = resp.json()
            if "choices" in data:  # Groq format
                _raw["text"] = data["choices"][0]["message"]["content"]
            else:  # Gemini format (thinking parts hata kar)
                parts = data["candidates"][0]["content"]["parts"]
                _raw["text"] = "\n".join(
                    p.get("text", "") for p in parts if not p.get("thought")
                )
    except Exception as e:  # parse fail ho to stage (a) khali dikhega, test na ruke
        _raw["text"] = f"<raw parse fail: {e}>"
    return resp


ai.requests.post = _spy_post  # ab ai.py ke dono call isse honge


def video_context():
    # db ke videos cache se title+description (API call bilkul nahi)
    row = db._db().execute(
        "SELECT video_id FROM replies WHERE comment IN ('keepit', 'great😊') "
        "AND video_id IS NOT NULL AND video_id != '' LIMIT 1"
    ).fetchone()
    if not row:
        return "Test vlog: Haryanvi singing, vlog style video."
    got = db.get_video(row[0])
    if not got:
        return "Test vlog: Haryanvi singing, vlog style video."
    title, desc = got
    return f"{title}\n{desc}"


def show(comment):
    ctx = video_context()
    print(f"\n{'=' * 60}\nCOMMENT: {comment!r}")

    _raw.pop("text", None)  # purana raw na chhoop jaye
    reply = ai.make_reply("test video", ctx, comment)

    # (a) LLM ka raw output (strip/validate se PEHLE jaisa model ne bheja)
    print(f"(a) RAW LLM output : {_raw.get('text', '<koi call nahi hui>')!r}")
    # (b) validator/cleanup ke baad make_reply ka return (yehi main.py ko milta hai)
    print(f"(b) make_reply return: {reply!r}")
    # (c) db me kya save hota (wahi value jo save_reply jaati hai)
    if reply is not None:
        db.save_reply("space_test", "vid_test", comment, reply, "draft", "test")
        row = db._db().execute(
            "SELECT reply FROM replies WHERE comment_id = 'space_test'"
        ).fetchone()
        print(f"(c) db value        : {row[0]!r}")
        db._db().execute("DELETE FROM replies WHERE comment_id = 'space_test'")
        db._db().commit()

    # Extra: raw vs final me andar ke spacing ka farq (missing-space ka seedha proof)
    if _raw.get("text") and reply:
        import re as _re
        norm = lambda s: _re.sub(r"\s+", " ", s).strip()
        print(f"raw==final (normalized): {norm(_raw['text']) == norm(reply)}")


if __name__ == "__main__":
    show("keepit")
    show("great😊")
