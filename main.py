# main.py — bot ka EK RUN (loop nahi): naye comments -> emoji/filters -> triggers -> LLM -> save/post
# Chalao: venv\Scripts\python.exe main.py
# MODE="draft" (default) = YouTube par KUCH post nahi hota — sirf db me save

import logging  # sab activity bot.log me jaayegi (keys kabhi nahi)
import os  # bot.lock banane/mutane ke liye (O_EXCL = ek hi instance)
import random  # emoji templates + reply delay + loop jitter dono me random
import re  # unicode hyphens ko normal "-" me badalne ke liye
import sys  # console encoding + exit code
import time  # reply delay aur loop sleep ke liye
from pathlib import Path  # STOP/lock files dhoondne ke liye

# Windows console cp1252 hai — Devanagari/emoji print karne ke liye UTF-8 chahiye
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ai  # LLM reply (Groq -> Gemini fallback) + answer_institute
import config  # MODE, delays, limits, emoji lists
import db  # saara database code db.py me
import filters  # rule-based skip + emoji_kind
import pipeline  # comment -> reply ka EK path (test_institute bhi yahi use karta hai)
import templates  # fixed templates (emoji / praise / institute)
import triggers  # keyword canned replies
import youtube  # official YouTube Data API calls
import mock_youtube  # --mock / --mock-llm: test ke liye fake YouTube + fake LLM

# Kill switch: is folder me "STOP" naam ki file ho to post BAND + run turant band
STOP_FILE = Path(__file__).parent / "STOP"

# Token expire (invalid_grant) par user ko bilkul yahi message dikhana hai
TOKEN_EXPIRED_MSG = (
    "Token expire ho gaya. token.json delete karke python main.py --once chalao "
    "aur dobara login karo."
)

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


# Special unicode hyphens (U+2010/2011/2013/2014) — inko normal "-" me badalte hain
_UNI_HYPHEN_RE = re.compile("[‐‑–—]")


def _post_failure(e):
    # (reason, stop_run) — quota/rate par run rok do, baaki errors par aage badho
    if youtube.quota_exceeded(e):  # 403 quotaExceeded = aaj ka quota khatam
        db.mark_quota_exhausted(config.QUOTA_LIMIT)  # loop aaj ke baaki runs skip karega
        return "post_quota", True
    status = getattr(getattr(e, "resp", None), "status", None)
    if status == 429:  # rateLimitExceeded — thodi der baad retry
        return "post_rate", True
    if status == 403:  # commentsDisabled/forbidden — sirf ye comment fail, run chalta rahe
        return "post_forbidden", False
    low = str(e).lower()
    if "quota" in low:  # apna QUOTA_LIMIT wala error
        db.mark_quota_exhausted(config.QUOTA_LIMIT)
        return "post_quota", True
    if "rate" in low and "limit" in low:  # "generate" jaise shabd se false-positive na ho
        return "post_rate", True
    return "post_error", False  # baaki errors — failed save karke aage badho


def _sleep_until_stop(seconds):
    # Sleep chhote chunks me — beech me STOP aaye to turant False (loop band)
    end = time.time() + max(0.0, seconds)
    while time.time() < end:
        if STOP_FILE.exists():
            return False
        time.sleep(min(1.0, end - time.time()))
    return not STOP_FILE.exists()


def _is_network_error(e):
    # Connection/timeout/DNS errors (built-in + requests/urllib3/socket) ya Google 5xx
    if isinstance(e, (ConnectionError, TimeoutError)):
        return True
    if getattr(getattr(e, "resp", None), "status", 0) >= 500:
        return True
    return (type(e).__module__ or "").startswith(("requests.", "urllib3.", "socket."))


def _backoff_seconds(prev):
    # Network backoff: 60s se shuru, har fail par double, max 15 min
    return min(15 * 60, max(60, int(prev) * 2))


def _loop_sleep_seconds():
    # Normal interval + jitter: 5 min ± 30 sec (pattern na lage)
    return config.CHECK_INTERVAL_MIN * 60 + random.uniform(-30, 30)


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
    try:
        comments, fetch_skips = youtube.fetch_new_comments(max_results=50)
    except youtube.QuotaExceededError as e:
        # Local QUOTA_LIMIT khatam — aaj ke baaki runs skip
        db.mark_quota_exhausted(config.QUOTA_LIMIT)
        print(f"{e} — aaj ke baaki runs skip.")
        return
    except Exception as e:
        if youtube.quota_exceeded(e):  # YouTube ka 403 quotaExceeded
            db.mark_quota_exhausted(config.QUOTA_LIMIT)
            print("YouTube quota khatam (403) — aaj ke baaki runs skip.")
            return
        raise  # token/network error — upar wala handler dekhega
    skips = dict(fetch_skips)  # is run ke saare skip reasons isi dict me count hote hain
    total_seen = len(comments) + sum(fetch_skips.values())  # API se kitne naye mile
    print(f"Comments mile: {total_seen} "
          f"({len(comments)} process + {sum(fetch_skips.values())} pehle se skip)")
    if not comments:
        print("Koi naya comment nahi mila jo process karne layak ho.")

    counts = {"emoji": 0, "trigger": 0, "llm": 0, "institute": 0, "praise": 0,
              "draft": 0, "posted": 0, "failed": 0}
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
            reply = templates.emoji_reply(ai._detect_language(text), text.strip())
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
                # --- 4) Reply ka path: pipeline.handle_comment (Step 6 — test_institute
                # bhi Yahi function use karta hai, dono ka reply hamesha same) ---
                def _video_ctx():
                    # Video info sirf normal (non-institute) path me chahiye
                    title, description = youtube.get_video_info(c["video_id"])
                    notes = youtube.get_video_notes(c["video_id"])  # video_notes/<id>.md ho to
                    return title, (description + "\n\n" + notes).strip()

                def _video_notes():
                    # video_notes/<id>.md — owner-fact (camera/mic) lookup ke liye
                    return youtube.get_video_notes(c["video_id"])

                label, reply, _chunks, reason = pipeline.handle_comment(
                    text, video_ctx=_video_ctx,
                    institute_enabled=config.INSTITUTE_MODE,
                    notes_fn=_video_notes,
                )
                source = ("institute" if label == "institute_info"
                          else "praise" if label == "praise" else "llm")

                if reason:
                    # reason = skip (criticism/spam/personal/mode off/bot-ka-sawaal/
                    #              owner-jaankari-nahi) ya fail
                    status = "skipped" if reason in (
                        "criticism", "spam", "personal_question", "institute_mode_off",
                        "asks_if_bot", "needs_owner"
                    ) else "failed"
                    db.save_reply(c["comment_id"], c["video_id"], text, "", status, reason)
                    skips[reason] = skips.get(reason, 0) + 1
                    if status == "skipped":
                        logger.info("SKIP %s reason=%s text=%s", c["comment_id"], reason, short)
                        print(f"[SKIP] ({reason}) {short}")
                    else:
                        counts["failed"] += 1
                        logger.warning("FAILED %s reason=%s text=%s",
                                       c["comment_id"], reason, short)
                        print(f"[FAILED] {short}")
                    continue

                counts[source] += 1

        # --- Special unicode hyphens normal "-" me + markdown hatao (plain text) ---
        # (validator ke baad, db save/post se pehle — har reply par ek hi jagah:
        #  LLM/institute reply ai.py me already stripped, yahan trigger/emoji cover)
        reply = filters.strip_markdown(_UNI_HYPHEN_RE.sub("-", reply))

        # --- 6) Save karo: auto = YouTube par post, draft = sirf db ---
        # (emoji + trigger + llm + institute — sab ka reply yahin se hokar jaata hai)
        # SAFETY: institute reply LIVE tabhi jab (profile zedking) YA (user ne
        # khud INSTITUTE_LIVE_ON_PERSONAL=True kiya ho). Akela kafi nahi —
        # MODE=auto (niche if) + --live (youtube.post_reply ka fail-safe) dono
        # bhi chahiye. Warna institute reply hamesha draft me save hogi.
        institute_live_ok = config.CHANNEL_PROFILE == "zedking" or (
            config.INSTITUTE_LIVE_ON_PERSONAL and live
        )
        force_draft = source == "institute" and not institute_live_ok
        if config.MODE == "auto" and not force_draft:
            # --live (live mode) = zyada strict limit, warna normal per-run limit
            limit = config.MAX_REPLIES_PER_RUN_LIVE if live else config.MAX_REPLIES_PER_RUN
            if posted_this_run >= limit:
                # Aaj ki limit poori — baaki comments agli run me process honge
                break
            if posted_this_run > 0:
                # do replies ke beech random 20-60 sec gap (spam policy)
                delay = random.randint(
                    config.REPLY_DELAY_MIN_SEC, config.REPLY_DELAY_MAX_SEC
                )
                if not _sleep_until_stop(delay):
                    print("STOP file mila — run turant band.")
                    break
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
    print(f"Institute replies   : {counts['institute']}")
    print(f"Draft save (draft)  : {counts['draft']}")
    print(f"Posted (auto mode)  : {counts['posted']}")
    print(f"Failed              : {counts['failed']}")
    print(f"Quota aaj           : {db.quota_used_today()}/{config.QUOTA_LIMIT} units")
    print(f"Mode                : {config.MODE} | live={live}")


def loop_mode(live):
    # Har CHECK_INTERVAL_MIN minute me ek run, +/- 30 sec jitter (pattern na lage)
    backoff = 0  # network fail par badhta hai, successful run par reset
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
                backoff = 0  # run chal gaya — backoff reset
        except youtube.TokenExpiredError:
            raise  # token expire = loop band, main() exit code 3 dega
        except Exception as e:
            if youtube.quota_exceeded(e) or isinstance(e, youtube.QuotaExceededError):
                # Aaj ka quota khatam — marker set, aage koi API call nahi
                db.mark_quota_exhausted(config.QUOTA_LIMIT)
                print("YouTube quota khatam — aaj ke baaki runs skip.")
                backoff = 0
            elif _is_network_error(e):
                backoff = _backoff_seconds(backoff)
                logger.warning("Network error — %d sec baad retry: %s", backoff, e)
                print(f"Network error — {backoff} sec baad retry.")
            else:
                # Koi aur run fail — log karke agla chalne do (bot kabhi na mare)
                logger.exception("Loop run fail — agla run chalega")
                print("Run fail (poora error bot.log me) — agla run chalta rahega.")
                backoff = 0
        _touch_lock()  # instance zinda hai — lock ki mtime fresh
        if not _sleep_until_stop(backoff or _loop_sleep_seconds()):
            print("STOP file mila — loop band.")
            break


def main():
    args = sys.argv[1:]
    # Typo pakadne ke liye unknown flag pehle hi rok do
    allowed = ("--once", "--loop", "--live", "--mock", "--mock-llm")
    unknown = [a for a in args if a not in allowed]
    if unknown:
        print(f"Unknown flag: {' '.join(unknown)} — options: {', '.join(allowed)}")
        sys.exit(2)
    live = "--live" in args  # asli posting ka switch (MODE=auto ke saath bhi chahiye)
    loop = "--loop" in args  # na ho to ek hi run (--once = default)
    mock = "--mock" in args  # real YouTube ki jagah FakeYouTube
    mock_llm = "--mock-llm" in args  # real LLM ki jagah fixed fake replies

    # Fake LLM se real YouTube par post karna khatarnak hai — isliye mock zaroori
    if mock_llm and not mock:
        print("--mock-llm ke saath --mock bhi chahiye (fake reply real YouTube par na jaaye).")
        sys.exit(2)
    if mock:
        mock_youtube.install()
        print("MOCK mode: FakeYouTube — real YouTube API call nahi hogi.")
    if mock_llm:
        mock_youtube.install_llm()
        print("MOCK LLM: fixed fake replies — real Groq/Gemini call nahi hogi.")

    if not _acquire_lock():  # ek hi instance — doosra chala to bahar
        sys.exit(1)
    try:
        if loop:
            loop_mode(live)
        else:
            run(live=live)
    except youtube.TokenExpiredError:
        # token.json revoke/expire — browser se dobara login hi ek raasta hai
        print(TOKEN_EXPIRED_MSG)
        sys.exit(3)
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
