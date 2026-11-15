# pipeline.py — comment se reply tak ka EK path (Step 6)
# Pehle main.py aur test_institute.py dono apna-apna routing code chalate the —
# isi liye dono ka reply alag aa sakta tha. Ab DONO yahi function call karte hain:
#   main.py         -> pipeline.handle_comment(...)
#   test_institute  -> pipeline.handle_comment(...)
# Isse "main me X, test me Y" wala mismatch khatam — ek jagah, ek logic.

import logging  # errors log karne ke liye (keys kabhi print nahi)

import ai  # institute + normal LLM reply
import config  # mode/caps
import intent  # comment ka label
import knowledge  # knowledge chunks (institute answers ke liye)
import templates  # fixed templates (praise/thanks)

logger = logging.getLogger(__name__)

# In labels par reply KABHI nahi jaata (criticism/spam/personal sawaal)
SKIP_LABELS = ("criticism", "spam", "personal_question")


def handle_comment(text, video_ctx=None, institute_enabled=True, notes_fn=None):
    """Ek comment ka reply — sabse upar se niche tak (labels + reply).

    Args:
        text: comment ka text
        video_ctx: callable -> (title, context) — sirf normal (non-institute)
            LLM path me call hota hai (video info tabhi fetch ho, jab zarurat ho)
        institute_enabled: False = institute replies chhod do (mode off)
        notes_fn: callable -> video_notes/<id>.md ka text (owner-fact lookup)

    Returns:
        (label, reply, chunks, reason)
          label  = intent label
          reply  = reply text ya None (skip/fail me None)
          chunks = use kiye gaye knowledge chunks
          reason = skip/fail ka reason ("" = reply ban gaya)
    """
    label = intent.classify_comment(text, "")

    if label in SKIP_LABELS:
        return label, None, [], label

    if label == "asks_if_bot":
        # "bot ho kya / AI hai?" — bot kuch nahi bolega, owner khud jawab dega
        return label, None, [], "asks_if_bot"

    if label == "institute_info":
        if not institute_enabled:
            return label, None, [], "institute_mode_off"
        chunks = knowledge.search(text, top_k=3)
        reply = ai.answer_institute(text, chunks)
        if reply is None:
            return label, None, chunks, "institute_fail"
        return label, reply, chunks, ""

    # --- Video ka FACTUAL sawaal (camera/mic/editing/location/music/upload time) ---
    # Ye praise se PEHLE check hota hai — "video bahut achha, kaunsa camera tha?"
    # jaise mixed comment me bhi sawaal poochha gaya hai (owner ko dikhna chahiye).
    field = ai.owner_question_field(text)
    if field:
        # 1) pehle video_notes/<video_id>.md, 2) phir knowledge/owner_facts.md
        notes = ""
        if notes_fn:
            try:
                notes = notes_fn() or ""
            except Exception as e:  # notes padhne me dikkat — fact nahi milega
                logger.warning("video notes padhe nahi ja sake: %s", e)
                notes = ""
        fact = knowledge.facts_from_notes(notes).get(field) or knowledge.owner_facts().get(field)
        if not fact:
            # Jaankari owner ke paas nahi hai — reply NAHI (needs_owner)
            return label, None, [], "needs_owner"
        reply = ai.answer_fact(fact, text)
        if reply is None:
            return label, None, [], "llm_fail"
        return label, reply, [], ""

    if label == "praise":
        # Tareef ka chhota thanks — template se (LLM nahi), repeat nahi hoga
        return label, templates.praise(ai._detect_language(text)), [], ""

    # Normal (video) LLM path — video context tabhi chahiye jab yahan aaye
    title, context = video_ctx() if video_ctx else ("", "")
    reply = ai.make_reply(title, context, text)
    if reply is None:
        return label, None, [], "llm_fail"
    return label, reply, [], ""
