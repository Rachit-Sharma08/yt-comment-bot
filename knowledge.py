# knowledge.py — knowledge/zedking_info.md ko CHUNKS me todta hai aur search karta hai
# Koi network call nahi — sirf local file padho. Koi error ho to crash NAHI (empty chunks)

import logging
import os
import re
from datetime import date, datetime, timedelta

import config

logger = logging.getLogger(__name__)

# Chunk = dict {heading, source, text} — text me heading + poora body + source taaki
# validator (ai.py) reply ke numbers ko ISI text se match kar sake
_CHUNKS = None  # pehli call par load hoga (module-level cache)

# Last updated ki date is date se purani ho to warning (crash nahi)
STALE_DAYS = 30


def _parse_last_updated(text):
    # File ke upar "Last updated: 2026-11-14" likha hota hai — usi se date nikalo
    m = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None  # galat format = warning skip, crash nahi


def _check_stale(text):
    # 30 din se purani file par WARNING do (knowledge ab bhi chalegi — sirf alert)
    d = _parse_last_updated(text)
    if d and date.today() - d > timedelta(days=STALE_DAYS):
        logger.warning(
            "Knowledge file %s ki 'Last updated' %s hai — %d din purani "
            "(%d din se zyada). Institute se naya version le lo.",
            config.KNOWLEDGE_FILE, d, (date.today() - d).days, STALE_DAYS,
        )
        print(f"[WARN] Knowledge file purani hai (Last updated: {d}) — institute se update le lo.")


def _split_sections(text):
    # "## " headings se sections todo (## 1. overview, ## 4. Courses waghera)
    lines = text.splitlines()
    sections, cur, buf = [], None, []
    for ln in lines:
        if ln.startswith("## "):
            if cur is not None:
                sections.append((cur, "\n".join(buf)))
            cur, buf = ln.strip(), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        sections.append((cur, "\n".join(buf)))
    return sections


def _section_source(body):
    # Section ke aakhir me "**Source:** ..." line hoti hai — wahi chunk ka source
    m = re.search(r"\*\*Source[^*]*:\*\*\s*(.+)", body)
    return m.group(1).strip() if m else ""


def load_chunks(force=False):
    """File ko chunks me todo (cache ke saath). Missing/broken file = [] (crash nahi).

    Chunking rule: "#### " = har course apna chunk, "### " = har branch apna chunk,
    warna poora section ek chunk. Har chunk me heading + source URL hota hai.
    """
    global _CHUNKS
    if _CHUNKS is not None and not force:
        return _CHUNKS

    path = config.KNOWLEDGE_FILE
    if not os.path.exists(path):
        logger.error("Knowledge file nahi mili: %s — institute replies disable.", path)
        _CHUNKS = []
        return _CHUNKS

    with open(path, encoding="utf-8") as f:
        text = f.read()

    _check_stale(text)  # purani ho to warning (upar defined)

    chunks = []
    for heading, body in _split_sections(text):
        src = _section_source(body)
        # Kya is section me aur sub-headings hain? (#### = courses, ### = branches)
        marker = "#### " if "\n#### " in "\n" + body else ("### " if "\n### " in "\n" + body else None)
        if marker:
            parts, cur, buf = [], None, []
            for ln in body.splitlines():
                if ln.startswith(marker):
                    if cur is not None:
                        parts.append((cur, "\n".join(buf)))
                    cur, buf = ln.strip(), []
                elif cur is not None:
                    buf.append(ln)
            if cur is not None:
                parts.append((cur, "\n".join(buf)))
            for sub_head, sub_body in parts:
                # Course/branch ka apna URL chunk text me rahe (validator ko chahiye)
                url_m = re.search(r"- URL:\s*(\S+)", sub_body)
                source = url_m.group(1) if url_m else src
                chunks.append({
                    "heading": sub_head.lstrip("# ").strip(),
                    "source": source,
                    "text": sub_head + "\n" + sub_body + f"\nSource: {source}",
                })
        else:
            chunks.append({
                "heading": heading.lstrip("# ").strip(),
                "source": src,
                "text": heading + "\n" + body,
            })

    _CHUNKS = chunks
    logger.info("Knowledge chunks bane: %d (%s)", len(chunks), path)
    return chunks


def _query_terms(query):
    # Chhote ASCII words + Devanagari words dono nikalo (lowercase)
    return set(w.lower() for w in re.findall(r"[A-Za-z0-9+#]{2,}|[\u0900-\u097F]{2,}", query))


def search(query, top_k=3):
    """Query ke liye top_k chunks return karo (best pehle). Kuch na mile to []."""
    chunks = load_chunks()
    if not chunks:
        return []

    q_terms = _query_terms(query)
    q_low = query.lower()

    # Query ka concept kaunsa (synonym group) — us group ke chunk words ko bonus
    hit_groups = [g for g in config.SYNONYMS if any(t.lower() in q_low for t in g)]

    # Query me course name mila? Us course ke chunk ko strong bonus
    q_course = None
    for name in config.COURSE_NAMES:
        if re.search(r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])", q_low):
            q_course = name.lower()
            break

    scored = []
    for ch in chunks:
        low = ch["text"].lower()
        head_low = ch["heading"].lower()
        score = 0
        # 1) Seedha keyword overlap (heading me mile to double)
        for t in q_terms:
            if t in low:
                score += 2 if t in head_low else 1
        # 2) Course-name match (query + chunk dono me ho to +5)
        if q_course and q_course in low:
            score += 5
        # 3) Synonym-group bridge (query "फीस" ho to "Fee:" wala chunk bhi mile)
        for g in hit_groups:
            if any(t.lower() in low for t in g):
                score += 2
        if score > 0:
            scored.append((score, ch))

    scored.sort(key=lambda x: -x[0])  # sabse pehle = sabse relevant
    return [ch for _, ch in scored[:top_k]]


if __name__ == "__main__":
    # Offline self-check — API call nahi, sirf file + logic
    chs = load_chunks(force=True)
    print(f"chunks: {len(chs)}")
    assert len(chs) > 30, "courses ke chunks kam padhe"
    # Har chunk me heading + source hone chahiye (validator ke liye zaroori)
    assert all(c["heading"] and c["text"] for c in chs)
    r = search("CCC course ki fees kitni hai")
    assert r and "CCC" in r[0]["heading"], f"CCC search fail: {[c['heading'] for c in r]}"
    r2 = search("kaithal me institute kahan hai")
    assert r2, "address search khaali"
    r3 = search("Bitcoin kaise kharide")
    print("bitcoin hits:", len(r3))  # 0 bhi chalega (out of scope)
    print("knowledge self-check PASS")
