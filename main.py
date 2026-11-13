# main.py — bot ka EK RUN (loop nahi): naye comments -> filters -> triggers -> LLM -> save/post
# Chalao: venv\Scripts\python.exe main.py
# MODE="draft" (default) = YouTube par KUCH post nahi hota — sirf db me save

import logging  # sab activity bot.log me jaayegi (keys kabhi nahi)
import random  # replies ke beech random delay (spam policy)
import sys  # console encoding + exit code
import time  # reply delay ke liye sleep

# Windows console cp1252 hai — Devanagari/emoji print karne ke liye UTF-8 chahiye
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai  # LLM reply (Groq -> Gemini fallback)
import config  # MODE, delays, limits
import db  # saara database code db.py me
import filters  # rule-based skip
import triggers  # keyword canned replies
import youtube  # official YouTube Data API calls

# --- Logging: sirf bot.log me (file .gitignore me hai) ---
# comment text 100 char tak hi log hota hai; API keys kabhi log nahi hoti
logging.basicConfig(
    filename="bot.log",
    filemode="a",  # purana log mitao MAT — append hota rahega
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bot")

LOG_TEXT_LEN = 100  # log/print me comment text itna hi dikhega


def _short(text):
    # Ek line me + 100 char tak — output saaf, log chhota
    return (text or "").replace("\n", " ")[:LOG_TEXT_LEN]


def run():
    db.init_db()  # teeno tables banao (pehli baar zaroori)

    # --- 1) Naye comments lao (latest pehle; duplicates/own-channel youtube.py khud hataata hai) ---
    comments = youtube.fetch_new_comments(max_results=50)
    print(f"Comments mile: {len(comments)}")
    if not comments:
        print("Koi naya comment nahi mila — is run me karne ko kuch nahi.")
        return

    counts = {"skip": 0, "trigger": 0, "llm": 0, "draft": 0, "posted": 0, "failed": 0}
    posted_this_run = 0  # auto mode: kitne replies abhi post ho chuke

    for c in comments:
        text = c["text"]
        short = _short(text)  # 100-char wala version (log + print dono me)

        # --- 2) Rule-based skip — SABSE PEHLE, LLM bilkul nahi chalega ---
        skip, reason = filters.should_skip(text)
        if skip:
            # db me "skipped" + reason save — agli baar ye comment dobara na aaye
            db.save_reply(c["comment_id"], c["video_id"], text, "", "skipped", reason)
            counts["skip"] += 1
            logger.info("SKIP %s reason=%s text=%s", c["comment_id"], reason, short)
            print(f"[SKIP] ({reason}) {short}")
            continue

        # --- 3) Keyword trigger — canned reply mila to LLM ki zarurat hi nahi ---
        # (trigger replies par URL/phone validator NAHI lagta — sirf LLM reply par ai.py me lagta hai)
        reply = triggers.match_trigger(c["video_id"], text)
        source = "trigger"
        if reply:
            counts["trigger"] += 1
        else:
            # --- 4) LLM path: video info (cache-first) + notes file se context ---
            title, description = youtube.get_video_info(c["video_id"])
            notes = youtube.get_video_notes(c["video_id"])  # video_notes/<id>.md ho to
            context = (description + "\n\n" + notes).strip()  # dono ka combination
            reply = ai.make_reply(title, context, text)  # validation andar hi hoti hai
            source = "llm"
            if reply is None:
                # --- 5) LLM fail / validation fail -> status "failed" ---
                db.save_reply(c["comment_id"], c["video_id"], text, "", "failed", "llm_fail")
                counts["failed"] += 1
                logger.warning("FAILED %s text=%s", c["comment_id"], short)
                print(f"[FAILED] {short}")
                continue
            counts["llm"] += 1

        # --- 6) Save karo: auto = YouTube par post, draft = sirf db ---
        if config.MODE == "auto":
            if posted_this_run >= config.MAX_REPLIES_PER_RUN:
                # Aaj ki limit poori — baaki comments agli run me process honge
                break
            if posted_this_run > 0:
                # do replies ke beech random 20-60 sec gap (spam policy)
                time.sleep(
                    random.randint(config.REPLY_DELAY_MIN_SEC, config.REPLY_DELAY_MAX_SEC)
                )
            try:
                youtube.post_reply(c["comment_id"], reply)
            except Exception as e:
                # Post fail aur row save NAHI ki to agli baar reply DOBARA chala jaata
                # (duplicate reply = spam). Isliye failed row zaroor save karo.
                db.save_reply(c["comment_id"], c["video_id"], text, reply, "failed", "post_error")
                counts["failed"] += 1
                logger.error("POST-FAIL %s: %s", c["comment_id"], e)
                print(f"[POST-FAIL] {short} | {e}")
                continue
            db.save_reply(c["comment_id"], c["video_id"], text, reply, "posted", source)
            counts["posted"] += 1
            posted_this_run += 1
            logger.info("POSTED %s via=%s text=%s", c["comment_id"], source, short)
            print(f"[POSTED/{source}] {short} -> {reply}")
        else:
            # Draft mode (default = safe): reply sirf db me, print ho jaata hai
            db.save_reply(c["comment_id"], c["video_id"], text, reply, "draft", source)
            counts["draft"] += 1
            logger.info("DRAFT %s via=%s text=%s", c["comment_id"], source, short)
            print(f"[DRAFT/{source}] {short} -> {reply}")

    # --- Summary: is run me kya-kya hua ---
    print("\n=== SUMMARY ===")
    print(f"Comments mile       : {len(comments)}")
    print(f"Skip (filters)      : {counts['skip']}")
    print(f"Trigger replies     : {counts['trigger']}")
    print(f"LLM replies         : {counts['llm']}")
    print(f"Draft save (draft)  : {counts['draft']}")
    print(f"Posted (auto mode)  : {counts['posted']}")
    print(f"Failed              : {counts['failed']}")
    print(f"Quota aaj           : {db.quota_used_today()}/{config.QUOTA_LIMIT} units")
    print(f"Mode                : {config.MODE}")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        # Koi bhi API/quota error — run ruk jaaye par crash traceback na dikhe,
        # poora details bot.log me safe rehti hain
        logger.exception("Run fail")
        print(f"ERROR: {e}  (poora error bot.log me)")
        sys.exit(1)
