# -*- coding: utf-8 -*-
# print_dev_templates.py — Step 1: config ke SAARE Devanagari templates print
# (ek-ek karke — glued shabd check karne ke liye). Temp verification, commit nahi.
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import config

# config ke saare dicts me se Devanagari strings nikalo (path ke saath)
import types
def walk(obj, path):
    if isinstance(obj, types.ModuleType):
        for k in dir(obj):
            if k.isupper():  # sirf CONFIG CONSTANTS (INSTITUTE_TEMPLATES waghera)
                yield from walk(getattr(obj, k), k)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str) and any("\u0900" <= ch <= "\u097f" for ch in obj):
        yield path, obj

# Glued heuristic: 4+ code point ka Devanagari run jo 2 known words ka judam hoi
# (Step 1 ke liye chhota sa — asli checker reply_checks me Step 2 me aayega)
W = {"कोर्स", "कुछ", "लोकप्रिय", "कौन", "सा", "से", "के", "की", "का",
     "जानना", "चाहते", "हैं", "है", "बारे", "में", "पूछ", "रहे", "सभी",
     "देखें", "फीस", "अवधि", "लिस्ट", "नहीं", "करें", "कॉल", "लिए",
     "नाम", "लिख", "दीजिए", "चाहिए", "या", "बताइए", "सकते", "क्या",
     "कितनी", "कितना", "अलग", "यहाँ", "सेंटर", "एडमिशन", "फॉर्म",
     "पूरी", "जानकारी", "टॉपिक", "हमारे", "हमारी", "हमारा", "कर", "रह",
     "हो", "हों", "वाला", "वाले", "वाली"}

def glued(tok):
    n = len(tok)
    best = [-1] * (n + 1)
    best[0] = 0
    for end in range(1, n + 1):
        for start in range(end):
            if best[start] >= 0 and tok[start:end] in W:
                best[end] = max(best[end], best[start] + 1)
    return best[n] >= 2

import re
DEV = re.compile(r"[\u0900-\u097F]+")
total = bad = 0
for path, s in walk(config, "config"):
    total += 1
    hits = [t for t in DEV.findall(s) if glued(t)]
    flag = "  <-- GLUED!" if hits else ""
    if hits:
        bad += 1
    print(f"[{path}]{flag}\n  {s}")
print(f"\nTOTAL {total} Devanagari templates, GLUED {bad}")
