# filters.py — rule-based comment filtering: kis comment ka reply NAHI karna
# Koi LLM call nahi — sirf regex + config.py ki lists

import re  # URL/injection/emoji check ke liye

import config

# URL/domain wala pattern: http, www. ya koi bhi domain (.com, .xyz, .in...)
_URL_RE = re.compile(
    r"(?i)https?://|www\.|\b[\w-]+\.(?:com|in|xyz|net|org|io|me|co|tv|link)\b"
)

# Emoji characters ka pattern — flags, pictographs, symbols + ZWJ/variation selectors
_EMOJI_RE = re.compile(
    "["
    "\u2600-\u27BF"  # misc symbols + dingbats (☀❤⭐ wale bhi)
    "\u2B00-\u2BFF"  # arrows/symbols (⭐ etc.)
    "\uFE0F\u200D\u20E3"  # variation selector + ZWJ + keycap (emoji sequences ke liye)
    "\U0001F000-\U0001FAFF"  # saare modern emoji blocks (👍🔥😂 wale)
    "]"
)


def emoji_kind(text):
    """Sirf emoji wale comment ka kind: "positive" / "negative" / "unknown".

    Emoji-only nahi (ya khali) ho to "" — tab ye function lagana hi nahi.
    """
    t = (text or "").strip()
    if not t:
        return ""  # khali — main/skip handle karega

    leftover = _EMOJI_RE.sub("", t).strip()  # emoji hata kar kya bacha?
    if leftover:
        return ""  # emoji ke saath text bhi hai = emoji-only NAHI

    tokens = _EMOJI_RE.findall(t)
    if not tokens:
        return ""  # koi emoji hi nahi (jaise "!!!")

    # Har emoji char ko set me daalo — "❤️" = ❤ + variation selector (dono chahiye)
    pos = set("".join(config.POSITIVE_EMOJIS))
    neg = set("".join(config.NEGATIVE_EMOJIS))
    if all(ch in pos for ch in tokens):
        return "positive"  # sab emoji positive list me
    if any(ch in neg for ch in tokens):
        return "negative"  # koi bhi negative emoji mila
    return "unknown"  # pehchana nahi — reply safe side par mat karo


def strip_markdown(text):
    """Reply ka markdown hata kar plain text banao (YouTube comment plain text hai).

    **bold**, *italic*, __bold__, _italic_, `code`, '# heading', '- ' bullet,
    [text](url) -> sirf text. Emoji aur normal punctuation waisa hi rehta hai.
    """
    t = text or ""
    t = re.sub(r"\[([^\]\n]+)\]\([^)\n]*\)", r"\1", t)  # [text](url) -> text
    t = re.sub(r"\*\*([^\n]+?)\*\*", r"\1", t)  # **bold** -> bold
    t = re.sub(r"__([^\n]+?)__", r"\1", t)  # __bold__ -> bold
    # *italic* / _italic_ — sirf paired markers (user_name jaise NAHI chhodte)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"\1", t)
    t = re.sub(r"(?<![_\w])_([^_\n]+)_(?!_)", r"\1", t)
    t = re.sub(r"(?m)^\s*#+\s*", "", t)  # line-start "# heading" -> heading
    t = re.sub(r"(?m)^\s*[-*]\s+", "", t)  # line-start "- bullet" -> bullet
    t = t.replace("`", "")  # code-span markers, andar ka text rehta hai
    t = t.replace("**", "").replace("__", "")  # akshe reh gaye bold markers
    return t.strip()


def should_skip(comment_text):
    """(skip?, reason) return karo. Skip = True to reply bilkul mat karo."""
    text = (comment_text or "").strip()

    # 1) Khali ya sirf space/punctuation — \W_ hata do, kuch na bache = khaali
    #    (emoji wala case upar emoji_kind me handle hota hai, yahan nahi)
    if not re.sub(r"[\W_]+", "", text, flags=re.UNICODE):
        return True, "empty"

    # 2) Comment me URL ya domain ho (spam/self-promo)
    if _URL_RE.search(text):
        return True, "contains_url_or_domain"

    low = text.lower()

    # 3) Prompt-injection jaise phrases (config.py ki list)
    for phrase in config.INJECTION_PHRASES:
        if phrase in low:  # substring match — chhoti phrase bhi pakde
            return True, f"injection_phrase: {phrase}"

    # 4) Hate/gaali wala text — kabhi reply nahi (AGENTS.md: abusive comments skip)
    for word in config.ABUSE_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return True, "abusive"

    # 5) Criticism/scam ke shabd (config.py ki ALAG list) — polite reply bhi nahi
    for word in config.CRITICISM_WORDS:
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            return True, "criticism"

    return False, ""  # reply karo — koi dikkat nahi


if __name__ == "__main__":
    # emoji_kind ka offline self-check (API call nahi — sirf logic)
    assert emoji_kind("🔥") == "positive"
    assert emoji_kind("👍🏽") == "positive"  # skin tone ke saath bhi
    assert emoji_kind("😡👎") == "negative"
    assert emoji_kind("👻") == "unknown"
    assert emoji_kind("nice video 🔥") == ""  # emoji-only nahi
    assert emoji_kind(" ") == ""  # khali
    assert emoji_kind("!!!") == ""  # emoji nahi
    assert should_skip("   ")[0] and should_skip("   ")[1] == "empty"
    assert should_skip("chutiya") == (True, "abusive")
    assert should_skip("bkwwas") == (True, "criticism")
    assert should_skip("This scam video") == (True, "criticism")  # case-insensitive
    assert should_skip("nice video")[0] is False  # normal comment skip NAHI
    # strip_markdown: markdown hato, emoji/normal text chhodo
    assert strip_markdown("**Great** video!") == "Great video!"
    assert strip_markdown("*italic* word") == "italic word"
    assert strip_markdown("__bold__ and _und_") == "bold and und"
    assert strip_markdown("`code` here") == "code here"
    assert strip_markdown("# Heading\n- item\n- two") == "Heading\nitem\ntwo"
    assert strip_markdown("[Click](https://x.com)") == "Click"
    assert strip_markdown("user_name ❤️ 100% zyada") == "user_name ❤️ 100% zyada"
    assert strip_markdown("2 * 3 = 6?") == "2 * 3 = 6?"  # normal punctuation bacha
    print("filters self-check PASS")
