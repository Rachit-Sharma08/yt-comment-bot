# main.py — bot ka EK RUN (loop nahi): naye comments -> emoji/filters -> triggers -> LLM -> save/post
# Chalao: venv\Scripts\python.exe main.py
# MODE="draft" (default) = YouTube par KUCH post nahi hota — sirf db me save

import logging  # sab activity bot.log me jaayegi (keys kabhi nahi)
import os  # bot.lock banane/mutane ke liye (O_EXCL = ek hi instance)
import random  # emoji templates + reply delay + loop jitter dono me random
import sys  # console encoding + exit code
import time  # reply delay aur loop sleep ke liye
from pathlib import Path  # STOP/lock files dhoondne ke liye

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

# Lock file: ek hi instance chale (do bot ek saath reply na karein)
LOCK_FILE = Path(__file__).parent / "bot.lock"
# Loop5 min par chalta hai — 30 min kuch na karna = purana instance mar gaya
LOCK_STALE_SEC = 30 * 60

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


def _acquire_lock():
    # Ek hi instance chale: O_EXCL se lock banao (maujood ho to bahar)
    for _ in range(2):  # stale lock par ek baar kabza le kar dobara try
        try:
            fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())  # andar PID — debugging me kaam aayega
            os.close(fd)
            return True
        except FileExistsError:
            try:
                age = time.time() - LOCK_FILE.stat().st_mtime
            except FileNotFoundError:
                continue  # race me kisi ne delete kar di — dobara banao
            if age > LOCK_STALE_SEC:
                # Purana instance 30 min se kuch nahi kar raha = mar chuka — kabza le lo
                LOCK_FILE.unlink()
                continue
            print(f"Ek aur instance chal raha hai (bot.lock {int(age)}s purana) — main nahi chala.")
            return False
    return False


def _touch_lock():
    # Har loop iteration me lock ki mtime fresh — mtime stale na lage
    try:
        os.utime(str(LOCK_FILE), None)
    except FileNotFoundError:
        pass  # lock gayab to koi chheda — agla acquire handle kar lega


def _release_lock():
    # Apna lock mitao — finally me hai isliye Ctrl+C/exception par bhi chhoot jaata hai
    try:
        LOCK_FILE.unlink()
    except FileNotFoundError:
        pass


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


def loop_mode(live):
    # Har CHECK_INTERVAL_MIN minute me ek run, +/- 30 sec jitter (pattern na lage)
    while True:
        try:
            if STOP_FILE.exists():
                print("STOP file mila — loop band.")
                break
            if db.quota_used_today() >= config.QUOTA_LIMIT:
                # Aaj quota khatam — baaki runs SKIP (API call bhi nahi hoti)
                print(f"Quota {config.QUOTA_LIMIT} paar — aaj ke baaki runs skip.")
            else:
                run(live)
        except Exception:
            # Ek run fail — log karke agla chalne do (bot kabhi na mare)
            logger.exception("Loop run fail — agla run chalega")
            print("Run fail (poora error bot.log me) — agla run chalta rahega.")
        _touch_lock()  # instance zinda hai — lock ki mtime fresh
        try:
            # Interval + jitter: 5 min ± 30 sec
            time.sleep(config.CHECK_INTERVAL_MIN * 60 + random.uniform(-30, 30))
        except KeyboardInterrupt:
            print("\nCtrl+C — loop band.")
            break


def main():
    args = sys.argv[1:]
    # Typo pakadne ke liye unknown flag pehle hi rok do
    unknown = [a for a in args if a not in ("--once", "--loop", "--live")]
    if unknown:
        print(f"Unknown flag: {' '.join(unknown)} — options: --once (default), --loop, --live")
        sys.exit(2)
    live = "--live" in args  # asli posting ka switch (MODE=auto ke saath bhi chahiye)
    loop = "--loop" in args  # na ho to ek hi run (--once = default)

    if not _acquire_lock():  # ek hi instance — doosra chala to bahar
        sys.exit(1)
    try:
        if loop:
            loop_mode(live)
        else:
            run(live=live)
    finally:
        _release_lock()  # Ctrl+C/exception par bhi lock chhoot jaaye (stale na bane)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C = saaf band, traceback nahi
        print("\nCtrl+C — bot saaf band.")
    except Exception as e:
        # Koi bhi API/quota error — crash traceback na dikhe, details bot.log me
        logger.exception("Run fail")
        print(f"ERROR: {e}  (poora error bot.log me)")
        sys.exit(1)
