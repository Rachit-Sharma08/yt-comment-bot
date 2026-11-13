# main.py — bot ka EK RUN (loop nahi): naye comments -> emoji/filters -> triggers -> LLM -> save/post
# Chalao: venv\Scripts\python.exe main.py
# MODE="draft" (default) = YouTube par KUCH post nahi hota — sirf db me save

import logging  # sab activity bot.log me jaayegi (keys kabhi nahi)
import random  # emoji templates + reply delay dono me random
import sys  # console encoding + exit code
import time  # reply delay ke liye sleep
from pathlib import Path  # STOP kill-switch file dhoondne ke liye

# Windows console cp1252 hai — Devanagari/emoji print karne ke liye UTF-8 chahiye
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai  # LLM reply (Groq -> Gemini fallback)
import config  # MODE, delays, limits, emoji lists
import db  # saara database code db.py me
import filters  # rule-based skip + emoji_kind
import triggers  # keyword canned replies
import youtube  # official YouTube Data API calls

# Kill switch: is folder me "STOP" naam ki file ho to post BAND + run turant band
STOP_FILE = Path(__file__).parent / "STOP"

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


def _post_failure(e):
    # (reason, stop_run) — 403/quota/rate wale error par run wahin rok do
    status = getattr(getattr(e, "resp", None), "status", None)
    if status in (403, 429):  # Google API: quotaExceeded / rateLimitExceeded
        return f"post_{status}", True
    low = str(e).lower()
    if "quota" in low:  # apna QUOTA_LIMIT wala error ya API ka quotaExceeded
        return "post_quota", True
    if "rate" in low and "limit" in low:  # "generate" jaise shabd se false-positive na ho
        return "post_rate", True
    return "post_error", False  # baaki errors — failed save karke aage badho


def run(live=False):
    db.init_db()  # teeno tables banao (pehli baar zaroori)

    # --live flag sirf yahan se set hota hai — youtube.post_reply isi ko dekhta hai
    youtube.LIVE = live

    # --- Kill switch: STOP file ho to run shuru hi mat ho (ek bhi post nahi) ---
    if STOP_FILE.exists():
        print("STOP file mila — run turant band (koi post nahi).")
        return

    # --- 1) Naye comments lao (too_old/already_replied youtube.py khud db me save kar chuka) ---
    comments, fetch_skips = youtube.fetch_new_comments(max_results=50)
    skips = dict(fetch_skips)  # is run ke saare skip reasons isi dict me count hote hain
    total_seen = len(comments) + sum(fetch_skips.values())  # API se kitne naye mile
    print(f"Comments mile: {total_seen} "
          f"({len(comments)} process + {sum(fetch_skips.values())} pehle se skip)")
    if not comments:
        print("Koi naya comment nahi mila jo process karne layak ho.")

    counts = {"emoji": 0, "trigger": 0, "llm": 0, "draft": 0, "posted": 0, "failed": 0}
    posted_this_run = 0  # auto mode: kitne replies abhi post ho chuke

    for c in comments:
        # STOP beech me aa gaya to yahin break — aage koi post nahi hoga
        if STOP_FILE.exists():
            print("STOP file mila — run turant band.")
            break
        text = c["text"]
        short = _short(text)  # 100-char wala version (log + print dono me)

        # --- 2a) Emoji-only comment — LLM nahi, seedha template reply (Step 0) ---
        kind = filters.emoji_kind(text)
        if kind == "positive":
            # Daily cap: aaj ke itne emoji replies ho chuke to aage skip
            if db.emoji_replies_today() >= config.MAX_EMOJI_REPLIES_PER_DAY:
                db.save_reply(c["comment_id"], c["video_id"], text, "", "skipped", "emoji_cap")
                skips["emoji_cap"] = skips.get("emoji_cap", 0) + 1
                logger.info("SKIP %s reason=emoji_cap text=%s", c["comment_id"], short)
                print(f"[SKIP] (emoji_cap) {short}")
                continue
            # Template me {e} = viewer ka apna emoji wapas; random template se variety
            reply = random.choice(config.EMOJI_REPLY_TEMPLATES).format(e=text.strip())
            source = "emoji"
            counts["emoji"] += 1
        elif kind in ("negative", "unknown"):
            # Hate wala emoji ya pehchana nahi — safe side par skip, reply NAHI
            reason = "negative_emoji" if kind == "negative" else "unknown_emoji"
            db.save_reply(c["comment_id"], c["video_id"], text, "", "skipped", reason)
            skips[reason] = skips.get(reason, 0) + 1
            logger.info("SKIP %s reason=%s text=%s", c["comment_id"], reason, short)
            print(f"[SKIP] ({reason}) {short}")
            continue
        else:
            # --- 2b) Rule-based skip — emoji-only NAHI hai to yahan (empty/abusive/url/injection) ---
            skip, reason = filters.should_skip(text)
            if skip:
                # db me "skipped" + reason save — agli baar ye comment dobara na aaye
                db.save_reply(c["comment_id"], c["video_id"], text, "", "skipped", reason)
                skips[reason] = skips.get(reason, 0) + 1
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
        # (emoji + trigger + llm — teeno ka reply yahin se hokar jaata hai)
        if config.MODE == "auto":
            # --live (live mode) = zyada strict limit, warna normal per-run limit
            limit = config.MAX_REPLIES_PER_RUN_LIVE if live else config.MAX_REPLIES_PER_RUN
            if posted_this_run >= limit:
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
                # Post fail: turant failed row save (warna agli baar reply DOBARA
                # chala jaata = duplicate = spam). Quota/rate error par run ruk jaata hai.
                reason, stop_run = _post_failure(e)
                db.save_reply(c["comment_id"], c["video_id"], text, reply, "failed", reason)
                counts["failed"] += 1
                logger.error("POST-FAIL %s reason=%s: %s", c["comment_id"], reason, e)
                print(f"[POST-FAIL] ({reason}) {short} | {e}")
                if stop_run:
                    print("Quota/rate error — run yahin rok diya.")
                    break
                continue
            # Post hone ke baad TURANT db me "posted" save (crash ho to record rahe)
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

    # --- Summary: is run me kya-kya hua (too_old/already_replied bhi yahin) ---
    print("\n=== SUMMARY ===")
    print(f"Comments mile (naye) : {total_seen}")
    print(f"  process hue        : {len(comments)}")
    for k in sorted(skips):
        print(f"  skip {k:16}: {skips[k]}")
    print(f"Emoji canned        : {counts['emoji']}")
    print(f"Trigger replies     : {counts['trigger']}")
    print(f"LLM replies         : {counts['llm']}")
    print(f"Draft save (draft)  : {counts['draft']}")
    print(f"Posted (auto mode)  : {counts['posted']}")
    print(f"Failed              : {counts['failed']}")
    print(f"Quota aaj           : {db.quota_used_today()}/{config.QUOTA_LIMIT} units")
    print(f"Mode                : {config.MODE} | live={live}")


if __name__ == "__main__":
    # --live flag = asli posting on (MODE=auto hone par bhi bina iske post nahi hoga)
    live = "--live" in sys.argv[1:]
    try:
        run(live=live)
    except Exception as e:
        # Koi bhi API/quota error — run ruk jaaye par crash traceback na dikhe,
        # poora details bot.log me safe rehti hain
        logger.exception("Run fail")
        print(f"ERROR: {e}  (poora error bot.log me)")
        sys.exit(1)
