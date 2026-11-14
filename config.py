# config.py — bot ki saari settings aur API keys ka ek hi source of truth
# Ye file sirf padhti hai (load) — koi network call ya side effect nahi

import os  # environment variables padhne ke liye

from dotenv import load_dotenv  # .env file ko process me load karne ke liye

load_dotenv()  # .env padh kar values ko os.environ me daal do (abhi .env khali hai)

# --- LLM API keys — sirf .env se, code me kabhi hardcode nahi ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")  # primary LLM (Groq) ki key, khali default
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # fallback LLM (Gemini) ki key, khali default

# --- LLM model names (official docs se verify kiye — andaza NAHI) ---
# Groq free/developer plan: https://console.groq.com/docs/rate-limits me listed
GROQ_MODEL = "openai/gpt-oss-120b"
# Gemini free tier: https://ai.google.dev/gemini-api/docs/pricing me "Free of charge"
# Note: gemini-3.8-flash naam sahi hai par test time par 503 (high demand) de raha tha;
# gemini-3.6-flash (stable, free) verified 200 — isliye fallback ke liye yehi
GEMINI_MODEL = "gemini-3.6-flash"

# --- Bot ka mode (draft/auto ka switch) ---
# "draft" = reply sirf database me save honge, YouTube par NAHI jayenge (default = safe)
# "auto"  = reply actually YouTube par post honge (hamesha pehle draft me test karo!)
# Fail-safe: agar .env me galat value ho to "auto" kabhi nahi banegi —
# koi bhi value jo "auto" na ho, draft hi treat hogi.
MODE = os.getenv("MODE", "draft")  # default "draft"

# --- YouTube API quota (AGENTS.md: daily limit 10,000 units) ---
# list call = 1 unit, reply post = 50 units. 8000 par bot khud rok jaayega
# taaki channel ka quota khatam na ho.
QUOTA_LIMIT = 8000  # aaj ke ye units upar nahi jaayenge

# --- Step 1: purane comments ka cutoff ---
# 24h se zyada purane top-level comments par reply NAHI — sirf fresh conversation pakdo
MAX_COMMENT_AGE_HOURS = 24

# --- Timing aur limits (spam policy ke hisaab se — AGENTS.md POLICY RULES) ---
CHECK_INTERVAL_MIN = 5  # har 5 minute me naye comments check honge
REPLY_DELAY_MIN_SEC = 20  # do replies ke beech random gap: kam se kam 20 sec
REPLY_DELAY_MAX_SEC = 60  # aur zyada se zyada 60 sec (random, spam na lage)
MAX_REPLIES_PER_RUN = 10  # ek run me zyada se zyada 10 replies (quota + spam safety)

# --- Step 2: LIVE mode (asli posting) ke liye zyada strict limit ---
# --live flag ke saath sirf 3 replies per run — pehle kam se kam post karke dekho
MAX_REPLIES_PER_RUN_LIVE = 3

# --- filters.py ki lists (rule-based skip ke liye) ---
# Basic gaali/abuse — Hindi (Roman) + English. Word-boundary se match hoti hai.
ABUSE_WORDS = [
    # English
    "fuck", "fucking", "shit", "bastard", "asshole", "motherfucker",
    "bitch", "dickhead",
    # Hindi (Roman me)
    "chutiya", "chutiye", "bhosdike", "gandu", "gandi", "randi",
    "bakchod", "haramkhor", "kutta", "kutti", "bewakoof",
]

# Prompt-injection jaise phrases — agar comment me ho to reply mat karo
INJECTION_PHRASES = [
    "ignore previous",
    "previous instructions",
    "system prompt",
    "system message",
    "instructions bhool",
    "api key",
    "disregard previous",
]

# --- Step 0: Emoji comments ka canned reply (LLM BILKUL nahi lagta) ---
# Sirf "sirf emoji" wale comments par chalega — text wale par filters/triggers/LLM
POSITIVE_EMOJIS = [
    "👍", "👌", "🔥", "❤️", "😂", "😍", "🙏",
    "🎉", "💯", "😊", "⭐", "👏",
    # Skin-tone modifiers — inke bina "👍🏻" unknown ho jaata tha
    "🏻", "🏼", "🏽", "🏾", "🏿",
]

# Negative/hate wale emoji — in par kabhi reply nahi (skip)
NEGATIVE_EMOJIS = ["👎", "😡", "🤬", "😠", "😢", "😭", "🤮", "😒", "🙄"]

# {e} = viewer ka apna emoji (comment wapas bhejta hai). Har reply alag lage — random chunta hai.
# Har template chhota + natural, aur {e} se PEHLE hamesha ek space (na to wo chipak jaaye)
EMOJI_REPLY_TEMPLATES = [
    "Thanks yaar {e}",
    "Shukriya! {e}",
    "Dhanyavaad {e}",
    "So sweet, thank you {e}",
    "Glad you liked it {e}",
    "Thanks for the love {e}",
    "Bahut achha laga {e}",
    "You made my day {e}",
    "Thanks for watching {e}",
    "Appreciate it {e}",
]

# Roz zyada se zyada itne emoji replies (spam policy: ek jaisa reply repeat na lage)
MAX_EMOJI_REPLIES_PER_DAY = 40

# --- Institute mode (ZedKing knowledge replies ka switch) ---
# CHANNEL_PROFILE: "personal" = purana vlog bot, "zedking" = institute channel
# SAFETY: institute replies sirf tab LIVE post hongi jab profile "zedking" ho
CHANNEL_PROFILE = os.getenv("CHANNEL_PROFILE", "personal")
# INSTITUTE_MODE: True = institute_info comments par knowledge se reply
# False = unhe "skipped / institute_mode_off" save karo (default safe = False)
INSTITUTE_MODE = os.getenv("INSTITUTE_MODE", "true").strip().lower() == "true"

# Knowledge file (chunks yahi se banenge — knowledge.py isko padhta hai)
KNOWLEDGE_FILE = "knowledge/zedking_info.md"

# Roz zyada se zyada itne contact/admission wale replies (phone/link cap — spam safety)
MAX_CONTACT_REPLIES_PER_DAY = 10

# --- LLM temperature (kam = zyada consistent, hallucination kam) ---
REPLY_TEMPERATURE = 0.3        # normal video replies (pehle 0.9 tha)
INSTITUTE_TEMPERATURE = 0.2    # institute knowledge replies (aur bhi strict)

# --- Knowledge search ke Hinglish synonyms (intent + search dono use karte hain) ---
# ek group = ek concept ke alag-alag tarike bolne ka
SYNONYMS = [
    ["fees", "fee", "kitni", "kitna", "price", "cost", "charge", "charges", "फीस", "कितने", "कितनी"],
    ["duration", "kitne mahine", "kitna time", "length", "mahine", "months", "समय", "अवधि", "कितने महीने"],
    ["address", "kahan", "location", "pata", "where", "kaha", "कहाँ", "पता", "किस जगह"],
    ["admission", "join", "dakhila", "enroll", "apply", "प्रवेश", "दाखिला", "एडमिशन"],
    ["branch", "centre", "center", "office", "शाखा", "ब्रांच"],
    ["contact", "phone", "number", "mobile", "call", "whatsapp", "संपर्क", "नंबर", "फोन"],
    ["timing", "time", "hours", "open", "khula", "समय", "टाइमिंग", "कब खुलता"],
    ["certificate", "certification", "certificate milega", "प्रमाणपत्र", "सर्टिफिकेट"],
    ["job", "placement", "rojgar", "career", "naukri", "नौकरी", "रोजगार", "प्लेसमेंट"],
    ["course", "courses", "kya sikhate", "kaun sa course", "कोर्स", "क्या सिखाते"],
    ["eligibility", "qualification", "who can join", "kaun kar sakta", "योग्यता", "पात्रता"],
]

# File me mojood course names (intent inke exact match ko bhi institute_info maanta hai)
# knowledge/zedking_info.md ke course headings se liye gaye hain
COURSE_NAMES = [
    "CCC", "BCC", "O Level", "A Level", "CCC Plus", "ACC", "DVP BCC", "DVP CCC",
    "Tally", "Tally Prime", "Python", "Java", "C Programming", "Cyber Security",
    "PHP", "MySQL", "IoT", "Financial Accounting", "Digital Accounting",
    "Office Automation", "Data Analysis", "Web Technology", "CCA", "ACCA",
    "Software Development", "Designing", "Publishing", "Hardware", "Networking",
    "Digital Marketing", "Expert Computer", "CCBA", "Web Designing",
    "Data Entry", "AI Digital Pro", "Stenography", "Steno", "Fire Technology",
    "Sub Fire Officer", "Fireman", "Health Sanitary Inspector", "Fire & Safety",
    "SSC", "HSSC", "Bank PO", "Banking",
]

# --- Step 3: Clarification options ke stopwords ---
# GENERIC shabd — inke match se kisi course ko option MAT banao (sirf meaningful
# topic words jaise marketing/tally/python/ccc se hi option banao)
COURSE_STOPWORDS = [
    # spec list
    "digital", "course", "computer", "basic", "advanced", "certificate",
    "training", "institute", "program",
    # sawaal ke generic shabd (ye bhi course topic nahi)
    "fees", "fee", "kitni", "kitna", "kitne", "kaise", "kya", "hai", "zedking",
]

# --- Criticism / scam wale comments — inka reply BILKUL nahi (abusive list se ALAG) ---
# Gaali (ABUSE_WORDS) yahan NAHI hai — yahan sirf tareef-negative, waste, fraud ke shabd
CRITICISM_WORDS = [
    "bkwwas", "bakwaas", "bakwas", "bekar", "bekaar", "ghatiya",
    "waste", "worst", "fake", "boring", "useless", "stupid", "fraud", "scam",
]
