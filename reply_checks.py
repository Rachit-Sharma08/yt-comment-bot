# reply_checks.py — reply ke automatic checks (sirf logic, koi network call nahi)
# test_e2e.py aur test_real_llm.py dono yahi use karte hain — ek hi rule, ek hi result.

import re
from urllib.parse import urlparse

import ai
import config
import filters

# --- Markdown markers (YouTube comment plain text hota hai) ---
_MARKDOWN_PATTERNS = [
    (r"\*\*", "bold **"),
    (r"__", "bold __"),
    (r"`", "code `"),
    (r"(?m)^\s*#{1,6}\s+", "heading #"),
    (r"(?m)^\s*[-*]\s+", "bullet -"),
    (r"\[[^\]\n]+\]\([^)\n]*\)", "link [text](url)"),
    (r"(?<![*\w])\*[^*\n]+\*(?!\*)", "italic *"),
    (r"(?<![_\w])_[^_\n]+_(?!_)", "italic _"),
]
_MARKDOWN_RES = [(re.compile(p), name) for p, name in _MARKDOWN_PATTERNS]

# --- Glued word: "aur10th" (letter-digit) ya "Marketingcourse" (do shabd jud gaye) ---
_GLUED_RE = re.compile(r"[a-z]\d|\d[a-z]|[a-z][A-Z]")
_GLUED_OK = {
    "10th", "11th", "12th", "3d", "4k", "5g", "b2b", "b2c", "mp3", "mp4",
    "iphone", "ipad", "ios", "youtube", "whatsapp", "linkedin", "powerpoint",
    "github", "javascript", "typescript", "chatgpt", "openai", "zedking",
}
# Compound check ke liye common shabd (10+ letter token me do shabd jud gaye?)
_COMMON = {
    "course", "courses", "video", "videos", "marketing", "digital", "institute",
    "admission", "fees", "fee", "duration", "address", "phone", "call", "karein",
    "karo", "hai", "aur", "ki", "ka", "ke", "me", "mein", "aap", "hum", "team",
    "study", "guide", "link", "details", "detail", "full", "more", "next",
    "watch", "like", "share", "subscribe", "channel", "youtube", "comment",
    "reply", "thanks", "thank", "you", "good", "great", "nice", "best", "new",
    "free", "online", "computer", "python", "java", "tally", "ccc", "level",
    "pass", "accha", "acha", "bahut", "bhai", "yaar", "kaise", "kya", "nahi",
}

# Internal words — public reply me kabhi nahi
_INTERNAL_RE = re.compile(
    r"(?i)\b(?:chunks?|file|knowledge|database|context|prompt|models?|unknown)\b"
)

# Pehle-person personal claim (bot apne baare me kuch nahi bolega)
_FIRST_PERSON_RE = re.compile(
    r"(?i)\b(?:main|mai|i)\s+(?:padh\w*|student|study|reht\w*|live|rahta|rahti)\b"
    r"|\bi(?:'|\u2019)?m\s+(?:a\s+)?student\b"
    r"|\bi\s+am\s+(?:a\s+)?student\b"
    r"|\bmera\s+naam\b|\bmy\s+name\s+is\b"
    r"|\u092e\u0948\u0902\s+(?:\u092a\u0922\u093c|\u0930\u0939\u0924)"
)

_URL_RE = re.compile(r"(?i)https?://[^\s<>\"')]+|www\.[^\s<>\"')]+")
_DEV_RE = re.compile(r"[\u0900-\u097F]")

# AI-jaise phrases + wade (promise) — config ki list se
_AI_LIKE_RE = re.compile(
    "|".join(re.escape(p) for p in config.AI_LIKE_PHRASES), re.IGNORECASE)
_PROMISE_RE = re.compile(
    "|".join(re.escape(p) for p in config.PROMISE_PHRASES), re.IGNORECASE)

# Em dash (—) aur en dash (–) — chhote casual reply me nahi chahiye
_DASH_RE = re.compile(r"[—–]")

# Third person institute ("ZedKing ke ... course") — "hum/hamare" chahiye
_THIRD_PERSON_RE = re.compile(r"(?i)\bzedking\s+(?:ke|ka|ki|me|ko|aur|and)\b")


def _word_at(text, start, end):
    # Match ke aas-paas ka poora word (glued token report karne ke liye)
    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "+#"):
        start -= 1
    while end < len(text) and (text[end].isalnum() or text[end] in "+#"):
        end += 1
    return text[start:end]


def _glued_hits(text):
    hits = []
    for m in _GLUED_RE.finditer(text or ""):
        word = _word_at(text, m.start(), m.end())
        if word.lower() in _GLUED_OK:
            continue
        hits.append(word)
    # Do common shabd bina space ke jude ho (Marketingcourse)
    for tok in re.findall(r"[A-Za-z]{10,}", text or ""):
        low = tok.lower()
        for i in range(3, len(low) - 2):
            if low[:i] in _COMMON and low[i:] in _COMMON:
                hits.append(tok)
                break
    return sorted(set(hits))


def _is_zedking(url):
    low = (url or "").lower().rstrip(".,);:!?")
    if low.startswith("www."):
        low = "https://" + low[4:]
    host = urlparse(low).netloc.lower()
    return host == "zedking.in" or host.endswith(".zedking.in")


def check_language(comment, reply, expected_lang):
    """Comment ki expected language ke hisaab se reply ki language check."""
    if expected_lang is None:
        return True, "n/a (emoji/empty)"
    has_dev = bool(_DEV_RE.search(reply or ""))
    if expected_lang == "Devanagari Hindi":
        return has_dev, "Devanagari expected"
    if has_dev:
        return False, "Devanagari reply for non-Devanagari comment"
    got = ai._detect_language(reply or "")
    return got == expected_lang, f"expected {expected_lang}, got {got}"


def check_reply(comment, reply, expected_lang=None):
    """(failed_checks, details) — reply par saare automatic checks."""
    fails, details = [], {}
    if not reply:
        return fails, details

    md = [name for rx, name in _MARKDOWN_RES if rx.search(reply)]
    if md:
        fails.append("markdown")
        details["markdown"] = md

    glued = _glued_hits(reply)
    if glued:
        fails.append("glued_word")
        details["glued_word"] = glued

    internal = _INTERNAL_RE.findall(reply)
    if internal:
        fails.append("internal_word")
        details["internal_word"] = internal

    fp = _FIRST_PERSON_RE.findall(reply)
    if fp:
        fails.append("first_person")
        details["first_person"] = fp

    urls = [u.rstrip(".,);:!?") for u in _URL_RE.findall(reply)]
    bad = [u for u in urls if not _is_zedking(u)]
    if bad:
        fails.append("url_outside_zedking")
        details["url_outside_zedking"] = bad
    if len(urls) > 1:
        fails.append("too_many_links")
        details["too_many_links"] = urls

    if len(reply) >= 280:
        fails.append("too_long")
        details["too_long"] = len(reply)

    ai_like = _AI_LIKE_RE.findall(reply)
    if ai_like:
        fails.append("ai_phrase")
        details["ai_phrase"] = sorted(set(ai_like))

    promise = _PROMISE_RE.findall(reply)
    if promise:
        fails.append("promise")
        details["promise"] = sorted(set(promise))

    if _DASH_RE.search(reply):
        fails.append("em_dash")
        details["em_dash"] = _DASH_RE.findall(reply)

    if _THIRD_PERSON_RE.search(reply):
        fails.append("third_person")
        details["third_person"] = _THIRD_PERSON_RE.findall(reply)

    lang_ok, lang_why = check_language(comment, reply, expected_lang)
    if not lang_ok:
        fails.append("language")
        details["language"] = lang_why

    return fails, details


def emoji_only(text):
    return filters.emoji_kind(text) != ""
