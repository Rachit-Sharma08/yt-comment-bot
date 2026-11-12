# triggers.py — keyword-based canned replies (LLM call BILKUL nahi lagta)
# Institute ki videos me "comment karo LINK/GUIDE" wale comments yahan aate hain

import json  # triggers.json padhne ke liye
import random  # replies me se ek random variant chunne ke liye
import re  # whole-word keyword match ke liye
from pathlib import Path
from urllib.parse import urlparse  # reply ka URL nikalne ke liye

TRIGGERS_FILE = Path(__file__).parent / "triggers.json"  # isi folder me triggers.json


def _extract_urls(text):
    # Reply me lage saare URLs nikalo (http://... wala hissa)
    return re.findall(r"https?://[^\s\"')]+", text)


def _host_allowed(host, domain):
    # host == domain ya uska subdomain (sub.zedking.in) — dono chalega
    return host == domain or host.endswith("." + domain)


def _load():
    # File load karo + CHECK: har reply ka URL allowed_domains me hi ho
    with open(TRIGGERS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    allowed = [d.lower() for d in data.get("allowed_domains", [])]
    for trig in data.get("triggers", []):
        for reply in trig.get("replies", []):
            for url in _extract_urls(reply):
                host = urlparse(url).netloc.lower()  # sirf domain nikalo
                if not any(_host_allowed(host, d) for d in allowed):
                    # Galat domain = error abhi do, chup-chap baad me fail hone se pehle
                    raise ValueError(
                        f"triggers.json: trigger '{trig.get('id')}' ka reply me "
                        f"allowed domain ke bahar URL hai: {url}"
                    )
    return data


# Import hi hote waqt load + validate — galat file ho to turant error
DATA = _load()


def match_trigger(video_id, comment_text):
    """Comment trigger se match ho to canned reply, warna None."""
    text = (comment_text or "").lower()  # case-insensitive match ke liye
    for trig in DATA.get("triggers", []):
        # video_ids me "*" ya ye video_id hona chahiye
        video_ids = trig.get("video_ids", [])
        if "*" not in video_ids and video_id not in video_ids:
            continue
        for keyword in trig.get("keywords", []):
            # whole word match: "link" par "linkedin" NAHI pakde, Devanagari bhi chalega
            if re.search(r"\b" + re.escape(keyword.lower()) + r"\b", text):
                replies = trig.get("replies", [])
                if replies:
                    return random.choice(replies)  # 2-3 variants me se random
    return None  # koi trigger nahi mila → LLM ko jaana padega
