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
GEMINI_MODEL = "gemini-3.8-flash"

# --- Bot ka mode (draft/auto ka switch) ---
# "draft" = reply sirf database me save honge, YouTube par NAHI jayenge (default = safe)
# "auto"  = reply actually YouTube par post honge (hamesha pehle draft me test karo!)
# Fail-safe: agar .env me galat value ho to "auto" kabhi nahi banegi —
# koi bhi value jo "auto" na ho, draft hi treat hogi.
MODE = os.getenv("MODE", "draft")  # default "draft"

# --- Timing aur limits (spam policy ke hisaab se — AGENTS.md POLICY RULES) ---
CHECK_INTERVAL_MIN = 5  # har 5 minute me naye comments check honge
REPLY_DELAY_MIN_SEC = 20  # do replies ke beech random gap: kam se kam 20 sec
REPLY_DELAY_MAX_SEC = 60  # aur zyada se zyada 60 sec (random, spam na lage)
MAX_REPLIES_PER_RUN = 10  # ek run me zyada se zyada 10 replies (quota + spam safety)

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
