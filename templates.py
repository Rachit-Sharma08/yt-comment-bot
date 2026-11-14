# templates.py — FIXED reply templates (Step 3) + link lines (Step 4)
# LLM BILKUL nahi — sirf config.py ke template strings uthao aur placeholders bharo
# Teeno languages (Roman Hinglish / English / Devanagari Hindi) hamesha available

import random  # variant chunne ke liye (2 variants hain har case me)

import config  # template strings + link templates
import knowledge  # sirf main_phone() ke liye (contact section ka number)

# Agar kisi language ka template na mile to Roman Hinglish par gir jao (crash nahi)
FALLBACK_LANG = "Roman Hinglish"


def pick(kind, language, **kw):
    """config.INSTITUTE_TEMPLATES[kind][language] me se ek variant + placeholders bharo.

    kind: "clarify" | "unknown" | "no_course"
    kw: {A}, {B} (clarify) ya {phone} (unknown)
    """
    variants = config.INSTITUTE_TEMPLATES[kind].get(language)
    if not variants:
        variants = config.INSTITUTE_TEMPLATES[kind][FALLBACK_LANG]
    return random.choice(variants).format(**kw)


def clarify(language, titles):
    """Step 3a — course ka naam clear nahi: do short names wala sawaal.

    Sirf 1 option ho to no_course template (sawaal "{A} ya {B}" banana galat hota).
    """
    if len(titles) < 2:
        return no_course(language)
    return pick("clarify", language, A=titles[0], B=titles[1])


def no_course(language):
    """Step 3c — comment me course ka naam hi nahi mila."""
    return pick("no_course", language)


def unknown(language):
    """Step 3b — jawab file me nahi / UNKNOWN: phone ke saath call karne ko kaho.

    Phone sirf knowledge file ke contact section se (main_phone).
    """
    return pick("unknown", language, phone=knowledge.main_phone())


def link_line(language, url):
    """Step 4 — course/admission page ka chhota closing line + URL (hubahu)."""
    variants = config.COURSE_LINK_TEMPLATES.get(language)
    if not variants:
        variants = config.COURSE_LINK_TEMPLATES[FALLBACK_LANG]
    return random.choice(variants).format(url=url)


def contact_reply(language, phone, address, url, with_phone=True, with_link=True):
    """Step 4 — address/admission/contact intent: phone + address + admission link.

    Jo part allowed hai (cap ke hisaab se) wahi lagta hai — max ek link.
    """
    parts = config.CONTACT_REPLY_PARTS.get(language) or config.CONTACT_REPLY_PARTS[FALLBACK_LANG]
    out = []
    if with_phone and phone:
        out.append(random.choice(parts["phone"]).format(phone=phone))
    if address:
        out.append(random.choice(parts["address"]).format(address=address))
    if with_link and url:
        out.append(random.choice(parts["link"]).format(url=url))
    return " ".join(out)
