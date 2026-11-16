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
# 3 languages x 8+ variants (voice_samples.md ke andaaz me — casual, chhote)
EMOJI_REPLY_TEMPLATES = {
    "Roman Hinglish": [
        "Thanks yaar {e}", "Shukriya {e}", "Arre waah, thanks {e}",
        "Dil se shukriya {e}", "Appreciate it {e}", "Shukriya, maza aa gaya {e}",
        "Thanks a lot {e}", "Thanks bhai, dil khush kar diya {e}",
        "Love it, thanks for watching {e}", "Mast, thanks yaar {e}",
    ],
    "English": [
        "Thanks a lot {e}", "Appreciate it {e}", "Thank you so much {e}",
        "Love it, thanks for watching {e}", "Thanks for the love {e}",
        "You made my day {e}", "Nice one, thanks {e}", "Thanks, glad you liked it {e}",
        "Cheers for watching {e}", "Thanks for watching {e}",
    ],
    "Devanagari Hindi": [
        "धन्यवाद {e}", "शुक्रिया {e}", "बहुत बढ़िया, धन्यवाद {e}",
        "दिल से धन्यवाद {e}", "आपका प्यार {e}", "शुक्रिया, मज़ा आ गया {e}",
        "बहुत बहुत धन्यवाद {e}", "आपके साथ बने रहो {e}", "प्यारा लगा, शुक्रिया {e}",
        "धन्यवाद दोस्त {e}",
    ],
}

# --- Tareef (praise) ka reply: LLM NAHI, seedha template (chhota + casual) ---
# 3 languages x 8+ variants — voice_samples.md ke andaaz me
PRAISE_REPLY_TEMPLATES = {
    "Roman Hinglish": [
        "Thanks yaar, aise hi support karte rehna 🙏",
        "Bahut shukriya bhai ❤️",
        "Arre waah, thanks yaar!",
        "Dil se shukriya 🙏",
        "Shukriya bhai, appreciate it ❤️",
        "Shukriya! Maza aa gaya padhke 😊",
        "Thanks bhai, dil khush kar diya",
        "Mast, thanks yaar 😄",
        "Thanks a lot, bahut achha laga",
        "Love it yaar, thanks for watching!",
    ],
    "English": [
        "Thanks a lot, means a lot 🙏",
        "Appreciate it bro ❤️",
        "Love it, thanks for watching!",
        "Thanks a lot, really appreciate it 😊",
        "Thanks for the love!",
        "You made my day!",
        "Thanks, that means a lot 🙏",
        "Cheers for watching!",
        "Thanks a lot, keep it up!",
        "Really appreciate it, thanks!",
    ],
    "Devanagari Hindi": [
        "धन्यवाद दोस्त, ऐसे ही साथ बने रहना 🙏",
        "बहुत बढ़िया, धन्यवाद 🙏",
        "दिल से धन्यवाद ❤️",
        "मज़ा आ गया, शुक्रिया 😊",
        "प्यारा लगा, धन्यवाद 🙏",
        "बहुत बहुत धन्यवाद दोस्त 🙏",
        "आपके साथ बने रहो, शुक्रिया ❤️",
        "शुक्रिया यार 😄",
    ],
}

# Roz zyada se zyada itne emoji replies (spam policy: ek jaisa reply repeat na lage)
MAX_EMOJI_REPLIES_PER_DAY = 40

# --- Institute mode (ZedKing knowledge replies ka switch) ---
# CHANNEL_PROFILE: "personal" = purana vlog bot, "zedking" = institute channel
# SAFETY: institute replies sirf tab LIVE post hongi jab profile "zedking" ho
CHANNEL_PROFILE = os.getenv("CHANNEL_PROFILE", "personal")
# INSTITUTE_MODE: True = institute_info comments par knowledge se reply
# False = unhe "skipped / institute_mode_off" save karo (default safe = False)
INSTITUTE_MODE = os.getenv("INSTITUTE_MODE", "true").strip().lower() == "true"

# --- Bot ki awaaz (voice) ---
# CHANNEL_PROFILE se decide hota hai:
#   personal = creator ki casual awaaz ("Thanks yaar")
#   zedking  = team ki "hum/hamare" awaaz ("Hamare CCC course ki fee ...")
# (CHANNEL_PROFILE ka default nahi badla — sirf usse VOICE nikala gaya)
VOICE = "creator" if CHANNEL_PROFILE == "personal" else "we"

# Style examples (LLM prompt me few-shot) + owner ki apni jaankari (facts)
VOICE_SAMPLES_FILE = "knowledge/voice_samples.md"
OWNER_FACTS_FILE = "knowledge/owner_facts.md"

# --- AI-jaise phrases: reply me KABHI nahi aane chahiye ---
# Validator inhe pakde to reply discard (aur reply_checks bhi check karta hai)
AI_LIKE_PHRASES = [
    "sawaal ke liye shukriya", "thanks for asking", "feel free to reach out",
    "i hope this helps", "hope this helps", "glad you enjoyed", "glad you liked",
    "kripya sampark karein", "please feel free", "happy to help",
    "let me know if", "if you have any questions", "don't hesitate",
    "as an ai", "as a language model", "here is the answer", "here's the answer",
    "thanks for your question", "thank you for asking", "feel free to ask",
    "i hope that helps", "hope that helps", "at your service",
]

# --- Wade (promise): reply me KABHI nahi ---
# "dekh ke bata hoon" / "I'll check and let you know" jaisa koi vaada nahi —
# jo jaankari owner_facts.md ya video_notes me nahi hai, wo bot bolega hi nahi
PROMISE_PHRASES = [
    "dekh ke bata", "dekhke bata", "dekh kar bata", "dekhkar bata",
    "check karke bata", "check kar ke bata", "pakad ke bata",
    "baad me bata", "baad mein bata", "baad me dekh", "baad me bata dunga",
    "baad me bataungi", "baad me batayenge", "baad mein batayenge",
    "get back to you", "i'll check and let you know", "i will check and let you know",
    "check and let you know", "let you know soon", "will get back",
    "looking into it", "i'll look into it", "i will look into it",
    "जानकारी लेकर बताएंगे", "देखकर बताऊंगा", "जाँच करके बताऊंगा", "बताएंगे",
]

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
    ["branch", "centre", "center", "office", "शाखा", "ब्रांच",
     "institute", "institution", "academy", "संस्थान", "अकादमी"],
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

# --- Institute templates (LLM BILKUL nahi) — 3 cases x 3 languages x 2-3 variants ---
# Awaaz: "hum/hamare" (team ki tarah). Kahi "ZedKing ke..." nahi, "please/kripya" nahi,
# aur koi wada nahi ("bata denge" jaisa future promise bhi nahi).
# clarify  = course ka naam clear nahi — {A}/{B} = short_name
# unknown  = jawab file me nahi — {phone} = institute main number
# no_course = course ka naam hi na mile — clarification + popular courses + URL
# not_in_list = course pucha par hamari list me nahi hai — {phone}
INSTITUTE_TEMPLATES = {
    # Step 4: institute/centre ka NAAM poocha ho — overview se naam + city
    "institute_name": {
        "Roman Hinglish": [
            "Hamara naam {institute_name} hai, {city} me. Courses ya address ke liye poochh sakte ho.",
            "{institute_name}, {city} me hai. Course ya fees ke baare me bata do.",
        ],
        "English": [
            "Our name is {institute_name}, in {city}. You can ask about courses or address.",
            "{institute_name} is in {city}. Ask us about courses or fees.",
        ],
        "Devanagari Hindi": [
            "हमारा नाम {institute_name} है, {city} में। कोर्स या पता के लिए पूछ सकते हैं।",
            "{institute_name}, {city} में है। कोर्स या फीस के बारे में बताइए।",
        ],
    },
    "clarify": {
        "Roman Hinglish": [
            "Kaun sa course chahiye: {A} ya {B}? Course ka naam likh do.",
            "Aap {A} ki baat kar rahe ho ya {B} ki? Naam likh do, uski detail yahi hai.",
            "{A} ya {B}, kaun sa course chahiye? Ek naam likh do bas.",
        ],
        "English": [
            "Which course do you mean: {A} or {B}? Just write the course name.",
            "Is it {A} or {B}? Write the course name and its details are here.",
            "{A} or {B}, which one? Write the name, that's all.",
        ],
        "Devanagari Hindi": [
            "कौन सा कोर्स चाहिए: {A} या {B}? कोर्स का नाम लिख दीजिए।",
            "आप {A} की बात कर रहे हैं या {B} की? नाम लिख दीजिए, उसकी जानकारी यहीं है।",
            "{A} या {B}, कौन सा कोर्स? बस नाम लिख दीजिए।",
        ],
    },
    "unknown": {
        "Roman Hinglish": [
            "Ye detail abhi hamare paas confirm nahi hai. Call karein: {phone}.",
            "Is baare me abhi confirm nahi hai humare paas. Call karein: {phone}.",
            "Ye jaankari abhi confirm nahi hai. Number: {phone}.",
        ],
        "English": [
            "This detail isn't confirmed on our side yet. Call us: {phone}.",
            "We can't confirm this one right now. Call us: {phone}.",
            "Not confirmed yet. Phone: {phone}.",
        ],
        "Devanagari Hindi": [
            "यह जानकारी अभी हमारे पास confirm नहीं है। कॉल करें: {phone}।",
            "इस बारे में अभी पुष्टि नहीं है। कॉल करें: {phone}।",
            "अभी confirm नहीं है। फोन: {phone}।",
        ],
    },
    # Step 6: course ka naam hi nahi mila — clarification + popular courses
    # {A}/{B}/{C} = pehle 3 courses, {courses_page_url} = listing URL
    "no_course": {
        "Roman Hinglish": [
            "Kaunsa course jaanna chahte ho? Kuch popular courses: {A}, {B}, {C}. Sab courses: {courses_page_url}",
            "Kaun sa course chahiye? Popular: {A}, {B}, {C}. Sab courses dekh lo: {courses_page_url}",
        ],
        "English": [
            "Which course do you want to know about? Some popular courses: {A}, {B}, {C}. All courses: {courses_page_url}",
            "Which course are you asking about? Popular ones: {A}, {B}, {C}. See all courses: {courses_page_url}",
        ],
        "Devanagari Hindi": [
            "कौन साकोर्स जानना चाहते हैं? कुछलोकप्रियकोर्स: {A}, {B}, {C}. सभी कोर्स: {courses_page_url}",
            "कौन सेकोर्स के बारे में पूछ रहे हैं? लोकप्रिय कोर्स: {A}, {B}, {C}. सभी कोर्स देखें: {courses_page_url}",
        ],
    },
    "not_in_list": {
        "Roman Hinglish": [
            "Ye course abhi hamari list me nahi hai. Available courses ke liye call karein: {phone}.",
            "Ye course hamari list me nahi hai abhi. Course list ke liye call karein: {phone}.",
            "Hamari list me ye course nahi hai. Call karein: {phone}.",
        ],
        "English": [
            "This course isn't on our list yet. For our available courses call us: {phone}.",
            "We don't have this course on the list right now. Call us for the course list: {phone}.",
            "This course isn't listed with us yet. Call us: {phone}.",
        ],
        "Devanagari Hindi": [
            "यह कोर्स अभी हमारी लिस्ट में नहीं है। उपलब्ध कोर्स के लिए कॉल करें: {phone}।",
            "यह कोर्स अभी हमारी लिस्ट में नहीं है। कोर्स लिस्ट के लिए कॉल करें: {phone}।",
            "हमारी लिस्ट में यह कोर्स नहीं है। कॉल करें: {phone}।",
        ],
    },
    # Step 5: comment ka TOPIC group mila — us group ke 1-3 courses ka sawaal
    # {courses} = short_names joined ("A", "A ya B", "A, B ya C")
    "topic_pick": {
        "Roman Hinglish": [
            "Aap {courses} ke baare me pooch rahe ho?",
            "Kya aap {courses} ke baare me pooch rahe ho?",
        ],
        "English": [
            "Are you asking about {courses}?",
            "Do you mean {courses}?",
        ],
        "Devanagari Hindi": [
            "क्या आप {courses} के बारे में पूछ रहे हैं?",
            "{courses} के बारे में पूछ रहे हैं?",
        ],
    },
    # Step 5: topic group mila par us group ka koi course list me nahi
    # {courses_page_url} = file ka courses listing URL, {phone} = main number
    "topic_no_course": {
        "Roman Hinglish": [
            "Is topic ka alag course hamari list me nahi mila. Sab courses yahan dekh sakte ho: {courses_page_url}. Call: {phone}.",
            "Is topic ke liye koi alag course list me nahi hai. Sab courses yahan dekh lo: {courses_page_url}. Call: {phone}.",
        ],
        "English": [
            "We don't have a separate course for this topic. See all courses: {courses_page_url}. Call: {phone}.",
            "No separate course for this topic right now. All courses here: {courses_page_url}. Call: {phone}.",
        ],
        "Devanagari Hindi": [
            "इस टॉपिक का अलग कोर्स हमारी लिस्ट में नहीं है। सभी कोर्स यहाँ देखें: {courses_page_url}। कॉल: {phone}।",
            "इस टॉपिक के लिए कोई अलग कोर्स अभी नहीं है। सभी कोर्स यहाँ: {courses_page_url}। कॉल: {phone}।",
        ],
    },
}

# --- Step 2 (rewrite): course field ke reply — sirf TEMPLATE, values file se hubahu ---
# Combined (fee + duration = default reply) — 3 variants x 3 languages
# {name} = course short_name, {fee}/{duration} = file ka value hubahu
COURSE_COMBINED_TEMPLATES = {
    "Roman Hinglish": [
        "Hamare {name} course ki fee {fee} hai, duration {duration}.",
        "Hamare {name} course ki fee {fee} hai aur duration {duration} hai.",
        "{name} course ki fee {fee} hai, duration {duration}.",
    ],
    "English": [
        "Our {name} course fee is {fee}, duration {duration}.",
        "Our {name} course fee is {fee} and duration is {duration}.",
        "The {name} course fee is {fee}, duration {duration}.",
    ],
    "Devanagari Hindi": [
        "हमारे {name} कोर्स की फीस {fee} है, अवधि {duration}।",
        "हमारे {name} कोर्स की फीस {fee} और अवधि {duration} है।",
        "{name} कोर्स की फीस {fee} है, अवधि {duration}।",
    ],
}

# Sirf EK field poochi ho — full-sentence template (2 variants x field x language)
# {name} = short_name, {value} = file ka value. "wale" aur " - " kabhi nahi.
COURSE_FIELD_TEMPLATES = {
    "fee": {
        "Roman Hinglish": [
            "Hamare {name} course ki fee {value} hai.",
            "{name} course ki fee {value} hai.",
        ],
        "English": [
            "Our {name} course fee is {value}.",
            "The {name} course fee is {value}.",
        ],
        "Devanagari Hindi": [
            "हमारे {name} कोर्स की फीस {value} है।",
            "{name} कोर्स की फीस {value} है।",
        ],
    },
    "duration": {
        "Roman Hinglish": [
            "Hamare {name} course {value} ka course hai.",
            "Hamare {name} course ki duration {value} hai.",
        ],
        "English": [
            "Our {name} course runs for {value}.",
            "Our {name} course duration is {value}.",
        ],
        "Devanagari Hindi": [
            "हमारे {name} कोर्स की अवधि {value} है।",
            "{name} कोर्स {value} का कोर्स है।",
        ],
    },
    "eligibility": {
        "Roman Hinglish": [
            "Hamare {name} course ke liye {value} chahiye.",
            "{name} course ki eligibility {value} hai.",
        ],
        "English": [
            "Our {name} course needs {value}.",
            "Our {name} course requires {value}.",
        ],
        "Devanagari Hindi": [
            "हमारे {name} कोर्स के लिए {value} चाहिए।",
            "{name} कोर्स की पात्रता {value} है।",
        ],
    },
    "mode": {
        "Roman Hinglish": [
            "Hamare {name} course {value} mode me hai.",
            "{name} course {value} me chalta hai.",
        ],
        "English": [
            "Our {name} course is available {value}.",
            "Our {name} course runs {value}.",
        ],
        "Devanagari Hindi": [
            "हमारे {name} कोर्स {value} मोड में है।",
            "{name} कोर्स {value} में चलता है।",
        ],
    },
    "certificate": {
        "Roman Hinglish": [
            "Hamare {name} course ka certificate {value} milta hai.",
            "{name} course ke baad {value} certificate milta hai.",
        ],
        "English": [
            "Our {name} course gives {value} certificate.",
            "You get {value} certificate from our {name} course.",
        ],
        "Devanagari Hindi": [
            "हमारे {name} कोर्स का {value} सर्टिफिकेट मिलता है।",
            "{name} कोर्स के बाद {value} सर्टिफिकेट मिलता है।",
        ],
    },
}

# Course matching ke liye stopwords (course name ka token na maana jaye)
COURSE_MATCH_STOPWORDS = COURSE_STOPWORDS + [
    "ki", "ka", "ke", "me", "mein", "hai", "hain", "ho", "kya", "kitni", "kitna",
    "kitne", "kaise", "batao", "bata", "kar", "karna", "karo", "karein", "karwana",
    "and", "for", "the", "is", "are", "a", "an", "of", "to", "in", "on", "my",
    "this", "that", "what", "which", "how", "you", "your", "please", "tell",
    "know", "about", "duration", "eligibility", "certificate", "mode", "admission",
    "address", "contact", "batch", "session", "year", "years",
    # Step 5: clarification ke shabd — ye course ke distinctive tokens nahi
    # ("Course ka naam kya hai?" ab no_course/clarification jaaye, not_in_list nahi)
    "name", "naam", "kaunsa", "kaun", "kaunsi", "sa", "likh",
    "popular", "kuch", "sab",
]

# --- Step 4: Link rule settings ---
# Course-specific fee/duration/eligibility reply ke aakhir me link add karna hai
LINK_IN_COURSE_REPLIES = True
MAX_LINK_REPLIES_PER_DAY = 15

# --- Step 3 (rewrite): contact/address/admission intent wala reply ---
# {phone} = institute ka main number, {address} = file ka address (", India" ke bina),
# {url} = admission page. Order: address -> phone -> link (spec).
# Hinglish/Hindi me English phrases ("Our address"/"Call us"/"We're at") NAHI.
CONTACT_REPLY_PARTS = {
    "Roman Hinglish": {
        "address": ["Hamara centre yahan hai: {address}.", "Centre yahan hai: {address}."],
        "phone": ["Call: {phone}.", "Hamara number: {phone}."],
        "link": ["Admission: {url}", "Admission form yahan: {url}"],
    },
    "English": {
        "address": ["Our centre is at {address}.", "The centre is at {address}."],
        "phone": ["Call: {phone}.", "Call us: {phone}."],
        "link": ["Admission: {url}", "Apply here: {url}"],
    },
    "Devanagari Hindi": {
        "address": ["हमारा सेंटर यहाँ है: {address}।", "सेंटर यहाँ है: {address}।"],
        "phone": ["कॉल: {phone}।", "फोन: {phone}।"],
        "link": ["एडमिशन: {url}", "एडमिशन फॉर्म यहाँ: {url}"],
    },
}

# --- Step 5: Institute reply ki max length (link ke saath) ---
MAX_INSTITUTE_REPLY_CHARS = 280
# Course link suffix templates (3 languages x 2 variants) — {url} = course chunk ka source URL
COURSE_LINK_TEMPLATES = {
    "Roman Hinglish": [
        "Poori detail: {url}",
        "Full details yahan dekh sakte hain: {url}",
    ],
    "English": [
        "Full details: {url}",
        "You can see full details here: {url}",
    ],
    "Devanagari Hindi": [
        "पूरी जानकारी: {url}",
        "पूरी जानकारी यहाँ देख सकते हैं: {url}",
    ],
}

# --- Criticism / scam wale comments — inka reply BILKUL nahi (abusive list se ALAG) ---
# Gaali (ABUSE_WORDS) yahan NAHI hai — yahan sirf tareef-negative, waste, fraud ke shabd
CRITICISM_WORDS = [
    "bkwwas", "bakwaas", "bakwas", "bekar", "bekaar", "ghatiya",
    "waste", "worst", "fake", "boring", "useless", "stupid", "fraud", "scam",
]
