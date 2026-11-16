# templates.py — FIXED reply templates (LLM BILKUL nahi — sirf config.py ke strings)
# Teeno languages (Roman Hinglish / English / Devanagari Hindi) hamesha available
# Voice samples (knowledge/voice_samples.md) ke andaaz me — chhote, casual

import random  # variant chunne ke liye
import re  # 2+ spaces theek karne ke liye

import config  # template strings + link templates
import knowledge  # sirf main_phone() ke liye (contact section ka number)

# Agar kisi language ka template na mile to Roman Hinglish par gir jao (crash nahi)
FALLBACK_LANG = "Roman Hinglish"

# --- Recent variants memory (last 5 repeat na ho) ---
# kind -> list of last 5 picked variants (process memory, restart pe reset)
_RECENT = {}


def _pick_recent(kind, variants):
    """Last 5 variants dobara na lage — memory me track karo."""
    if not variants:
        return ""
    recent = _RECENT.setdefault(kind, [])
    choices = [v for v in variants if v not in recent] or variants
    picked = random.choice(choices)
    recent.append(picked)
    if len(recent) > 5:
        recent.pop(0)
    return picked


def pick(kind, language, **kw):
    """config.INSTITUTE_TEMPLATES[kind][language] me se ek variant + placeholders bharo.

    kind: "clarify" | "unknown" | "no_course" | "not_in_list"
    kw: {A}, {B} (clarify) ya {phone} (unknown/no_course/not_in_list)
    """
    variants = config.INSTITUTE_TEMPLATES[kind].get(language)
    if not variants:
        variants = config.INSTITUTE_TEMPLATES[kind][FALLBACK_LANG]
    return _pick_recent(kind, variants).format(**kw)


def clarify(language, titles):
    """Course ka naam clear nahi: do short names wala sawaal.

    Sirf 1 option ho to no_course template (sawaal "{A} ya {B}" banana galat hota).
    """
    if len(titles) < 2:
        return no_course(language)
    return pick("clarify", language, A=titles[0], B=titles[1])


def no_course(language):
    """Comment me course ka naam hi nahi mila (ya match clear nahi)."""
    return pick("no_course", language)


def not_in_list(language):
    """Course pucha par wo hamari list me hai hi nahi."""
    return pick("not_in_list", language, phone=knowledge.main_phone())


def unknown(language):
    """Jawab file me nahi / UNKNOWN: phone ke saath call karne ko kaho.

    Phone sirf knowledge file ke contact section se (main_phone).
    """
    return pick("unknown", language, phone=knowledge.main_phone())


def course_reply(language, record, fields):
    """Course field ka reply — sirf template + file ke values (LLM nahi).

    record: knowledge.course_records() ka ek record
    fields: ["fee", "duration", ...]
      - fee+duration (default) -> combined template (3 variants/lang)
      - sirf 1 field -> us field ka full-sentence template (2 variants/lang)
      - aur koi combo -> har field ki sentence, space se join

    Koi field missing (None/UNKNOWN) ho to None — caller unknown template de.
    """
    name = record["short_name"]
    for field in fields:
        if not record.get(field):
            return None  # file me ye field nahi — answer mat bana

    def _field_sentence(field):
        tpls = (config.COURSE_FIELD_TEMPLATES.get(field, {}).get(language)
                or config.COURSE_FIELD_TEMPLATES[field][FALLBACK_LANG])
        return _pick_recent(f"field_{field}", tpls).format(
            name=name, value=record[field])

    if set(fields) == {"fee", "duration"}:
        tpls = (config.COURSE_COMBINED_TEMPLATES.get(language)
                or config.COURSE_COMBINED_TEMPLATES[FALLBACK_LANG])
        reply = _pick_recent("course_combined", tpls).format(
            name=name, fee=record["fee"], duration=record["duration"])
    else:
        # 1 field = uski sentence; zyada = sentences space se join
        reply = " ".join(_field_sentence(f) for f in fields)
    return re.sub(r"\s{2,}", " ", reply).strip()


def praise(language):
    """Tareef ka chhota thanks — template se (LLM nahi), repeat nahi hoga."""
    variants = (config.PRAISE_REPLY_TEMPLATES.get(language)
                or config.PRAISE_REPLY_TEMPLATES[FALLBACK_LANG])
    return _pick_recent("praise", variants)


def emoji_reply(language, emoji):
    """Emoji-only comment ka reply — template se (repeat nahi hoga)."""
    variants = (config.EMOJI_REPLY_TEMPLATES.get(language)
                or config.EMOJI_REPLY_TEMPLATES[FALLBACK_LANG])
    return _pick_recent("emoji", variants).format(e=emoji)


def link_line(language, url):
    """Course/admission page ka chhota closing line + URL (hubahu)."""
    variants = config.COURSE_LINK_TEMPLATES.get(language)
    if not variants:
        variants = config.COURSE_LINK_TEMPLATES[FALLBACK_LANG]
    return _pick_recent("link_line", variants).format(url=url)


def contact_reply(language, phone, address, url, with_phone=True, with_link=True,
                  with_address=True):
    """Address/admission/contact intent: phone + address + admission link.

    Jo part allowed hai (cap ke hisaab se) wahi lagta hai - max ek link.
    with_address=False -> chhota variant (280 char limit me address nahi samata)
    """
    parts = config.CONTACT_REPLY_PARTS.get(language) or config.CONTACT_REPLY_PARTS[FALLBACK_LANG]
    out = []
    if with_phone and phone:
        out.append(_pick_recent("contact_phone", parts["phone"]).format(phone=phone))
    if with_address and address:
        out.append(_pick_recent("contact_address", parts["address"]).format(address=address))
    if with_link and url:
        out.append(_pick_recent("contact_link", parts["link"]).format(url=url))
    return " ".join(out)
