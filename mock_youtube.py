# mock_youtube.py — FakeYouTube + FakeLLM: test/dry-run ke liye mock layer.
# Real YouTube API ki jagah sab kuch memory me chalta hai — koi network call nahi,
# koi post nahi. post_reply sirf self.posted list me record karta hai.
#
# Use:
#   fake = mock_youtube.install()        # youtube.* functions replace
#   mock_youtube.install_llm()           # ai/intent LLM calls replace
#   fake.add_comment("Nice video bro")   # comment feed me daalo
#
# main.py me: --mock (FakeYouTube) aur --mock-llm (FakeLLM) flags.

import logging

import ai
import db
import intent
import knowledge
import youtube

logger = logging.getLogger(__name__)

# Loop test ke liye auto-feed comments (institute nahi — personal profile par
# institute reply draft rehta hai aur har cycle dobara process hota hai)
_LOOP_TEXTS = [
    "Nice video bro",
    "Bhai ye camera kaunsa hai?",
    "🔥",
    "Bakwaas video, waste of time",
    "Guide please",
    "Subscribe to my channel http://spam.xyz",
    "👍🏽",
    "Which mic do you use?",
]


class FakeYouTube:
    """youtube.py ke 4 functions ki jagah — sab memory me, koi API call nahi."""

    def __init__(self, comments=None, video_title="Mock Video",
                 video_description="Mock video description.", auto_feed=0):
        self.comments = list(comments or [])  # saare comments (retry ke liye rehte hain)
        self.video_title = video_title
        self.video_description = video_description
        self.auto_feed = auto_feed  # har fetch par itne naye comments (loop test)
        self.posted = []  # [{"comment_id": ..., "text": ...}] — sirf record
        self.fetch_calls = 0
        self.post_calls = 0
        self._next_id = 1
        self._feed_i = 0
        # Error injection (test ke liye)
        self.fetch_error_every = 0  # har Nth fetch par ConnectionError
        self.post_error_every = 0   # har Nth post par RuntimeError
        self.post_error = None      # hamesha fail karne ke liye exception
        self.video_info = {}        # video_id -> (title, description)

    def add_comment(self, text, video_id="mockvid", author="Mock Viewer",
                    comment_id=None):
        # Unique id — db primary key + duplicate check ke liye
        cid = comment_id or f"mock-c{self._next_id:04d}"
        self._next_id += 1
        self.comments.append({
            "comment_id": cid,
            "video_id": video_id,
            "author": author,
            "author_channel_id": "mock-author",
            "text": text,
        })
        return cid

    def _auto_add(self):
        # Har fetch par naye comments — loop stability test ke liye
        for _ in range(self.auto_feed):
            text = _LOOP_TEXTS[self._feed_i % len(_LOOP_TEXTS)]
            self._feed_i += 1
            self.add_comment(text)

    def get_service(self):
        return self  # koi google client nahi

    def fetch_new_comments(self, max_results=50):
        # Real youtube.py jaisa: jo db me final status me hai use chhod do.
        # failed/llm_fail done NAHI hai — agle fetch par dobara aayega (retry).
        self.fetch_calls += 1
        if self.fetch_error_every and self.fetch_calls % self.fetch_error_every == 0:
            raise ConnectionError("mock network error (fetch)")
        self._auto_add()

        out = []
        for c in self.comments:
            if len(out) >= max_results:
                break
            if db.already_done(c["comment_id"]):
                continue
            out.append(c)
        return out, {}  # mock me too_old/already_replied skip nahi

    def get_video_info(self, video_id):
        if video_id in self.video_info:
            return self.video_info[video_id]
        return self.video_title, self.video_description

    def get_video_notes(self, video_id):
        return ""  # notes optional — mock me khali

    def post_reply(self, parent_comment_id, text):
        # Sirf list me record — YouTube par kuch NAHI jaata
        self.post_calls += 1
        if self.post_error is not None:
            raise self.post_error
        if self.post_error_every and self.post_calls % self.post_error_every == 0:
            raise RuntimeError("mock post error")
        self.posted.append({"comment_id": parent_comment_id, "text": text})


class FakeLLM:
    """ai/intent ke LLM calls ki jagah fixed replies — free-tier limit nahi lagti."""

    def __init__(self, fail_every=0, fail_first=0):
        self.reply_calls = 0
        self.fail_every = fail_every  # har Nth reply call par None (429 jaisa)
        self.fail_first = fail_first  # pehle N reply calls fail (retry test)

    def _reply_fails(self):
        self.reply_calls += 1
        if self.reply_calls <= self.fail_first:
            return True
        return bool(self.fail_every and self.reply_calls % self.fail_every == 0)

    def classify(self, text):
        # intent._llm_classify ki jagah — simple rule, koi API nahi
        low = (text or "").lower()
        words = ("camera", "mic", "editing", "software", "video", "vlog",
                 "shoot", "kahan", "कहां", "कहाँ", "kaise", "kya", "which",
                 "what", "how", "kab", "next", "वीडियो")
        return "video_question" if any(w in low for w in words) else "other"

    def _lang(self, comment):
        return ai._detect_language(comment)

    def make_reply(self, video_title, video_context, comment, provider=None,
                   temperature=None):
        if self._reply_fails():
            ai.LAST_MODEL = None
            return None
        lang = self._lang(comment)
        low = (comment or "").lower()
        if any(p in low for p in ("nice video", "great video", "bahut achha",
                                  "bahut acha", "great job", "keep it up",
                                  "mast video", "बहुत बढ़िया", "बहुत अच्छा")):
            kind = "praise"
        elif any(w in low for w in ("camera", "mic", "editing", "software",
                                    "kahan", "कहां", "कहाँ", "वीडियो")):
            kind = "video_question"
        else:
            kind = "other"
        ai.LAST_MODEL = "FakeLLM"
        return _REPLIES[lang][kind]

    def answer_fact(self, fact_text, comment):
        """Owner fact se reply ka mock — fact ke words, koi promise nahi."""
        if self._reply_fails():
            ai.LAST_MODEL = None
            return None
        ai.LAST_MODEL = "FakeLLM"
        return f"{fact_text}, yahi use karte hoon."

    def answer_institute(self, comment, chunks):
        # Institute reply ab TEMPLATE se banti hai (ai.answer_institute) — mock me
        # ye path chalti hai, isliye yahan kuch karne ki zarurat nahi.
        return None


# Fixed replies — plain text, no markdown, no URL, no internal words,
# koi first-person personal claim nahi, koi promise nahi, koi AI-phrase nahi.
_REPLIES = {
    "Devanagari Hindi": {
        "praise": "बहुत धन्यवाद! ऐसे ही साथ बने रहिए 🙏",
        "video_question": "यह बात वीडियो में नहीं है, इसलिए कुछ नहीं बताऊँगा।",
        "other": "वीडियो देखने के लिए धन्यवाद! ऐसे ही बने रहिए 🙏",
        "institute_course": "कोर्स की फीस और डिटेल्स के लिए इंस्टीट्यूट को कॉल करें: {phone}।",
        "institute_contact": "एडमिशन और पते की जानकारी के लिए इंस्टीट्यूट को कॉल करें: {phone}।",
    },
    "Roman Hinglish": {
        "praise": "Bahut shukriya! Aise hi saath bane rahiye.",
        "video_question": "Ye baat video me nahi hai, isliye kuch nahi bata sakta.",
        "other": "Video dekhne ke liye shukriya! Aise hi saath rahiye.",
        "institute_course": "Course ki fees aur details ke liye institute ko call karein: {phone}.",
        "institute_contact": "Admission aur address ki jaankari ke liye institute ko call karein: {phone}.",
    },
    "English": {
        "praise": "Thank you so much! Love the support.",
        "video_question": "That detail isn't in the video, so I can't say it for sure.",
        "other": "Thanks for watching! Love the support.",
        "institute_course": "For course fees and details, please call the institute: {phone}.",
        "institute_contact": "For admission and address details, please call the institute: {phone}.",
    },
}


def install(fake=None):
    """youtube.py ke functions ko FakeYouTube se replace karo."""
    fake = fake or FakeYouTube()
    youtube.get_service = fake.get_service
    youtube.fetch_new_comments = fake.fetch_new_comments
    youtube.get_video_info = fake.get_video_info
    youtube.get_video_notes = fake.get_video_notes
    youtube.post_reply = fake.post_reply
    logger.info("FakeYouTube installed — real YouTube call nahi hogi")
    return fake


def install_llm(fake=None):
    """ai.make_reply / ai.answer_fact / intent._llm_classify replace karo.

    Institute reply ab template se banti hai (ai.answer_institute) — us path ko
    real chhodte hain, sirf LLM classification ko None karte hain (network nahi).
    """
    fake = fake or FakeLLM()
    ai.make_reply = fake.make_reply
    ai.answer_fact = fake.answer_fact
    ai._llm_classify_course = lambda comment, records: None
    intent._llm_classify = fake.classify
    logger.info("FakeLLM installed — real Groq/Gemini call nahi hogi")
    return fake
