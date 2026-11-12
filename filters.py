# filters.py — rule-based comment filtering: kis comment ka reply NAHI karna
# Koi LLM call nahi — sirf regex + config.py ki lists

import re  # URL/injection/emoji check ke liye

import config

# URL/domain wala pattern: http, www. ya koi bhi domain (.com, .xyz, .in...)
_URL_RE = re.compile(
    r"(?i)https?://|www\.|\b[\w-]+\.(?:com|in|xyz|net|org|io|me|co|tv|link)\b"
)


def should_skip(comment_text):
    """(skip?, reason) return karo. Skip = True to reply bilkul mat karo."""
    text = (comment_text or "").strip()

    # 1) Khali ya sirf emoji/punctuation — \W_ hata do, kuch na bache = khaali
    if not re.sub(r"[\W_]+", "", text, flags=re.UNICODE):
        return True, "empty_or_emoji"

    # 2) Comment me URL ya domain ho (spam/self-promo)
    if _URL_RE.search(text):
        return True, "contains_url_or_domain"

    low = text.lower()

    # 3) Prompt-injection jaise phrases (config.py ki list)
    for phrase in config.INJECTION_PHRASES:
        if phrase in low:  # substring match — chhoti phrase bhi pakde
            return True, f"injection_phrase: {phrase}"

    # 4) Basic gaali/abuse (config.py ki list) — word-boundary match
    for word in config.ABUSE_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return True, f"abuse_word: {word}"

    return False, ""  # reply karo — koi dikkat nahi
