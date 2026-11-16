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


# Ye ALLCAPS shabd course ke CODE nahi hain (GST/AI/SSC jaise content words) —
# inko code mat maano, warna "Python Programming (AI)" jaise galat naam banenge
_NON_CODE = {
    "AI", "GST", "TDS", "SEO", "SEM", "BI", "IT", "SSC", "HSSC",
    "CGL", "CHSL", "MTS", "CET", "IBPS", "SBI", "RRB", "NIELIT",
}


def short_name(heading):
    """Course heading se chhota naam (spec Step 2) — clarification me yahi bologe.

    "18. Digital Marketing Course in Kaithal — DMA – SEO, Google Ads..." ->
    "Digital Marketing (DMA)" — SEO ke lambe hisse (" - ...", "(...)") hatao,
    " in Kaithal"/"Course" hatao, par course ka code (DMA, CCC, CDA) rakho.
    Mapping EK jagah = isi function me. Non-course heading waisa hi wapas.
    """
    if not re.match(r"^\d+\.\s*", heading):
        return heading  # course heading nahi (branch/section) — chheda mat
    t = re.sub(r"^\d+\.\s*", "", heading).strip()

    # --- Code nikalo (3 jagah se), NON_CODE shabd chhod kar ---
    code = None
    cands = []
    m = re.match(r"([A-Z][A-Z0-9]{1,4})\b", t)  # shuruaat me code: "CCC ..."
    if m:
        cands.append(m.group(1))
    parts = re.split(r"\s+[—–-]\s+", t, maxsplit=1)  # dash ke baad pehla word: "— DMA ..."
    if len(parts) > 1:
        m = re.match(r"([A-Z][A-Z0-9]{1,4})\b", parts[1].strip())
        if m:
            cands.append(m.group(1))
    m = re.search(r"\(([A-Z][A-Z0-9]{1,4})\)", t)  # paren me code: "(CDA)"
    if m:
        cands.append(m.group(1))
    for c in cands:
        if c not in _NON_CODE:
            code = c
            break

    # --- Naam saaf karo: subtitle, parens, " in Kaithal", "Course" hatao ---
    name = parts[0]  # pehla hissa = asli naam, aage ka lamba SEO subtitle
    name = re.sub(r"\s*\([^)]*\)", " ", name)  # "(...SEO...)" jaisa suffix
    name = re.sub(r"\s+in kaithal\s*$", "", name, flags=re.IGNORECASE)
    name = name.replace("Course", " ")  # "Digital Marketing Course" -> "Digital Marketing"
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"^(?:in\s+|&\s*)+", "", name, flags=re.IGNORECASE)  # "Course in & X" ka bacha hua
    name = name.strip(" ,&-")
    if code and not re.search(r"\b" + re.escape(code) + r"\b", name, re.IGNORECASE):
        name += f" ({code})"  # code naam me NAHI hai to jodo: DMA, CDA...
    return name or heading


def main_phone():
    """Institute ka MAIN number — contact section ke "Phone" line se (Step 3).

    Spec: phone sirf file ke contact section ka main number — doosre
    (mobile/landline) kabhi mat use. File me na mile to "" (crash nahi).
    """
    for c in load_chunks():
        if "contact" not in c["heading"].lower():
            continue
        m = re.search(r"\*\*Phone[^*]*:\*\*\s*(\+91-\d{10})", c["text"])
        if m:
            return m.group(1)
    return ""


def _contact_field(label):
    """Contact chunk se ek field (Phone/Address/Admission page) — file se hubahu."""
    for c in load_chunks():
        if "contact" not in c["heading"].lower():
            continue
        m = re.search(r"\*\*" + label + r"[^*]*:\*\*\s*(.+)", c["text"])
        if m:
            return m.group(1).strip()
    return ""


def contact_address():
    """Contact chunk ka address (Step 4 — address intent reply ke liye).

    Aakhri ", India" hata kar — reply chhota aur spec jaisa (Step 3).
    """
    addr = _contact_field("Address")
    return re.sub(r",\s*India\s*$", "", addr).strip()


def admission_url():
    """Admission page URL (Step 4 — contact/admission intent ka link)."""
    return _contact_field("Admission page")


def allowed_source_urls():
    """Knowledge file ke saare source URLs ka set (validator URL whitelist ke liye).

    Sirf zedking.in domain ke URLs whitelist me rakhte hain.
    """
    urls = set()
    for c in load_chunks():
        src = c.get("source", "")
        for u in re.findall(r"https?://[^\s,]+", src):
            u_clean = u.rstrip(".,)")
            if "zedking.in" in u_clean.lower():
                urls.add(u_clean)
    return urls


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
                h = sub_head.lstrip("# ").strip()
                chunks.append({
                    "heading": h,
                    "short": short_name(h),  # chhota course naam (clarification ke liye)
                    "source": source,
                    "text": sub_head + "\n" + sub_body + f"\nSource: {source}",
                })
        else:
            h = heading.lstrip("# ").strip()
            chunks.append({
                "heading": h,
                "short": short_name(h),  # non-course = waisa hi wapas
                "source": src,
                "text": heading + "\n" + body,
            })

    _CHUNKS = chunks
    logger.info("Knowledge chunks bane: %d (%s)", len(chunks), path)
    return chunks


def _query_terms(query):
    # Chhote ASCII words + Devanagari words dono nikalo (lowercase)
    return set(w.lower() for w in re.findall(r"[A-Za-z0-9+#]{2,}|[\u0900-\u097F]{2,}", query))


# ================= Owner facts (knowledge/owner_facts.md) =================
# File ka format: "Sawaal: Jawab" (ek line me ek cheez).
# Jawab khali ya UNKNOWN = bot us baare me jawab NAHI dega (needs_owner skip).
OWNER_FACT_FIELDS = {
    "camera": ["camera", "phone"],
    "gimbal": ["gimbal", "tripod"],
    "mic": ["mic"],
    "editing": ["editing", "software"],
    "music": ["music", "background", "track"],
    "location": ["kahan ke ho", "shehar", "city", "location"],
    "vlog_type": ["vlog banate", "type ke vlog"],
    "upload_time": ["upload kab", "upload hota"],
}

_OWNER_FACTS = None


def owner_facts():
    """Owner ki apni jaankari — {field: value ya None}.

    value None = file me us field ka jawab khali/UNKNOWN hai (bot jawab nahi dega).
    """
    global _OWNER_FACTS
    if _OWNER_FACTS is not None:
        return _OWNER_FACTS

    facts = {field: None for field in OWNER_FACT_FIELDS}
    try:
        with open(config.OWNER_FACTS_FILE, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        logger.warning("Owner facts file nahi mili: %s", config.OWNER_FACTS_FILE)
        _OWNER_FACTS = facts
        return facts

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if not val or "UNKNOWN" in val.upper():
            continue  # khali/UNKNOWN = fact pata nahi
        low = key.lower()
        for field, words in OWNER_FACT_FIELDS.items():
            if any(w in low for w in words):
                facts[field] = val
                break
    _OWNER_FACTS = facts
    return facts


def facts_from_notes(text):
    """video_notes/<id>.md se 'Field: value' pairs — owner field keys me.

    (owner_facts.md jaisa hi format: "Camera: iPhone 15 Pro")
    """
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if not val or "UNKNOWN" in val.upper():
            continue
        low = key.lower()
        for field, words in OWNER_FACT_FIELDS.items():
            if any(w in low for w in words):
                out.setdefault(field, val)
                break
    return out


# ================= Course records (structured) =================
_COURSE_RECORDS = None


def _clean_field(val):
    """UNKNOWN ya khaali value = None (bot guess nahi karega)."""
    if not val:
        return None
    val = val.strip()
    if not val or "UNKNOWN" in val.upper():
        return None
    return val


def course_records():
    """Har course ka structured record: fee/duration/eligibility/mode/certificate/url.

    Missing ya UNKNOWN field = None. (LLM nahi — sab file se hubahu)
    """
    global _COURSE_RECORDS
    if _COURSE_RECORDS is not None:
        return _COURSE_RECORDS

    recs = []
    for c in load_chunks():
        h = c["heading"]
        m = re.match(r"^(\d+)\.\s*(.+)$", h)
        if not m:
            continue  # course nahi (branch/section)
        body = c["text"]
        # Course me "Fee:" ya "Duration:" line hoti hai — section/branch me nahi
        if not re.search(r"^- (Fee|Duration):", body, re.M):
            continue
        rec = {
            "course_id": m.group(1),
            "name": m.group(2).strip(),
            "short_name": c["short"],
            "fee": None, "duration": None, "eligibility": None,
            "mode": None, "certificate": None, "url": None,
        }
        cert_mode = None
        for field, label in (("duration", "Duration"), ("fee", "Fee"),
                             ("eligibility", "Eligibility"), ("certificate", "Certificate/Mode")):
            mm = re.search(r"^- " + re.escape(label) + r":\s*(.+)$", body, re.M)
            if not mm:
                continue
            val = _clean_field(mm.group(1))
            if field == "certificate":
                cert_mode = val
            else:
                rec[field] = val
        # Certificate/Mode line se mode (Offline/Online) aur certificate alag
        if cert_mode:
            mm = re.search(r"(Offline[^/,\n]*|Online[^/,\n]*)", cert_mode)
            if mm:
                rec["mode"] = mm.group(1).strip()
            rec["certificate"] = re.split(r"[/,]", cert_mode)[0].strip() or None
        mu = re.search(r"^- URL:\s*(\S+)", body, re.M)
        if mu:
            rec["url"] = mu.group(1).strip()
        recs.append(rec)

    _COURSE_RECORDS = recs
    logger.info("Course records bane: %d", len(recs))
    return recs


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
    # short_name: heading se chhota naam + code (spec Step 2)
    assert short_name("18. Digital Marketing Course in Kaithal — DMA – SEO, Google Ads & Social Media") == "Digital Marketing (DMA)"
    assert short_name("11. Digital Accounting Course (CDA) in Kaithal") == "Digital Accounting (CDA)"
    assert short_name("25. CCC (NIELIT Course on Computer Concepts)") == "CCC"
    assert short_name("23. AI Digital Pro — Learn to build almost anything with AI") == "AI Digital Pro"
    assert short_name("31. Python Programming Course in Kaithal — AI · Data Science · Django") == "Python Programming"  # AI code NAHI
    assert short_name("38. Tally Prime Course in Kaithal — GST · Accounting") == "Tally Prime"  # GST code NAHI
    assert all(c["short"] for c in chs)  # har chunk ke paas short ho
    # Step 3: main number sirf contact section se (spec: doosre number nahi)
    assert main_phone() == "+91-9416111612", main_phone()
    print("knowledge self-check PASS")
