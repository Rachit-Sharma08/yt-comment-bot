# AGENTS.md — YouTube Comment Auto-Reply Bot

> Ye project-specific rules hain. Har nayi session me ye file padho.

---

## PROJECT

- **Kya hai:** Local PC par chalne wala Python bot. Mere YouTube channel par
  koi comment aaye to bot us video ke context (title, description, transcript)
  ke hisaab se relevant reply likhe aur YouTube Data API v3 se post kare.
- **Flow (har cycle):**
  1. Naye comments fetch karo
  2. Duplicate check karo (pehle se reply kiya hai ya nahi)
  3. Video context nikalo (title, description, transcript)
  4. AI se reply generate karao
  5. Reply post karo
  6. Database me save karo
  7. Har 5–10 min repeat karo
- **Mode:** Abhi mere personal vlog channel par test hoga, baad me
  institute/agency ke liye modify hoga. Replies final mode me automatic post
  hongi, par config me `MODE = "draft"` ya `"auto"` ka switch rahega.
  **Hamesha pehle draft me test karo.**
- **Deadline:** 4 din me build, 2 din testing.

## STACK (sab free)

| Kaam | Tool |
|---|---|
| Language | Python |
| YouTube API | YouTube Data API v3 (OAuth Desktop app, scope `youtube.force-ssl`) |
| LLM | Groq primary + Gemini fallback (API keys `.env` me) |
| Database | SQLite — **saara database code sirf `db.py` me**, taaki baad me Supabase par shift ho sake |
| Scheduler | `schedule` library ya Windows Task Scheduler |

- Koi paid service ya paid API use mat karna.

## POLICY RULES (zaroori)

- **Sirf official YouTube Data API use karo.** Scraping, browser automation
  ya unofficial tricks bilkul nahi.
- In sab ka palan karo:
  - YouTube API Services Terms of Service
  - YouTube Developer Policies
  - Google API Services User Data Policy
  - YouTube Community Guidelines (spam aur deceptive practices ke rules)
  - Groq / Gemini ki terms
  - **Kisi policy par shak ho to rukke mujhse poochho.**
- **Spam jaisa behavior nahi:**
  - Ek jaise replies repeat nahi
  - Replies ke beech random 20–60 sec delay
  - Quota ke andar raho (reply post = 50 units, daily limit 10,000 units)
  - Apne channel ke khud ke comments ko reply nahi
- **User data minimal rakho:** sirf comment id, video id, comment text,
  reply, status, time. Data kisi third party ko mat bhejo (sirf reply
  generate karne ke liye LLM API ko comment text jaati hai).
- **Secrets:** `client_secret.json`, `token.json`, `.env` kabhi commit ya
  print nahi hone chahiye.
- **Secrets files ko tum KABHI open, read ya cat mat karo** — `.env`,
  `token.json`, `client_secret.json`. Code unhe load kar sakta hai (jaise
  `config.py` `.env` padhta hai), par tum unka content nahi dekhoge.
- **AI reply me jhooth ya jaankari banao mat.** Jawab video se pata na ho to
  bolo ki "dekh ke batata hoon". Abusive / hateful / spam comments par reply
  mat karo.
- **Fee, duration, address, phone, link reply me tabhi aa sakte hain jab wo
  `knowledge/zedking_info.md` ke chunk me hubahu likhe hon.** LLM kabhi koi
  number, fee, phone, address ya link apni taraf se nahi banayega.
  **Validator ye check karega** (reply me har number/fee/phone/link/address
  chunk me exact hona chahiye — warna reply discard).
- **Bot kabhi pehle person me apne baare me kuch nahi bolega** (student,
  teacher, "main padhta hoon", kahan rehta hoon, umar, gender). Institute
  channel par "hum" ya "ZedKing team" ke roop me bolega. Personal channel
  par bhi channel ke malik ke baare me koi claim nahi.
- **Reply ki language hamesha comment ki language jaisi** — institute
  replies me bhi: Roman Hinglish comment → Roman Hinglish reply,
  English → English, Devanagari → Devanagari.
- **Jo jaankari video context me nahi hai wo andaze se nahi bolni** — na pata
  ho to comment ki language me bolo ki dekh ke batata hoon.

## AWAAZ + JAANKARI RULES (voice + facts — Step 1 & 2)

### Awaaz (voice)

- **Bot kabhi apni taraf se koi nayi personal baat nahi bolega** — kya kiya,
  kahan gaya, kaunsa camera/mic, kya khaya, kya mood me tha. Jo baat file me
  likhi nahi hai, wo nahi boli jayegi.
- **Institute channel par "hum / hamare / humari" ki awaaz** (team ki tarah).
  Kabhi third person me mat bolo — ❌ "ZedKing ke CCC course ki fee..." →
  ✅ "Hamare CCC course ki fee ₹6,000 hai."
- **Personal channel par creator ki casual awaaz** — chhote, comment jaisi lines.
- **Reply me AI-jaise phrases mat likho:** "Sawaal ke liye shukriya",
  "Thanks for asking", "Feel free to reach out", "I hope this helps",
  "Glad you enjoyed", "Kripya sampark karein". Em dash (—) aur lambe formal
  sentences bhi nahi. Chhota, casual, comment jaisi language.
- **"Bot ho kya / AI hai / real insaan ho / automatic reply hai" type comments
  par reply KABHI nahi.** db me status `skipped`, reason `asks_if_bot` — owner
  khud jawab dega. Keywords Hindi, Hinglish aur English me `intent.py` me hain.

### Jaankari (facts) — koi jhootha vaada nahi

- **Bot kabhi vaada nahi karega:** "dekh ke bata hoon", "I'll check and let you
  know", "baad me bataunga", "get back to you" — ye sab BAN hai (validator
  reply discard karta hai).
- **Video ka factual sawaal (camera, mic, editing app, location, music,
  upload time, gear) ka jawab sirf 2 jagah se aata hai:**
  1. `video_notes/<video_id>.md` (pehle)
  2. `knowledge/owner_facts.md` (uske baad)
- **Reply me jo bhi naam, model, number ya jagah ho wo fact ki line me hubahu
  hona chahiye** — warna reply discard.
- **Jawab na mile to reply KABHI nahi** — db me status `skipped`, reason
  `needs_owner` (owner khud jawab dega; `review.py --owner` se list dikhti hai).
- **Tareef/feedback par chhota thanks** — `knowledge/voice_samples.md` ke
  andaaz me (LLM nahi, template).
- **Thanks/praise/emoji templates ke 8+ variants** rakho (Hinglish, English,
  Hindi) aur last 5 variants dobara na lage (memory me track).

## CODING STYLE (mujhe seekhna hai)

- Mai beginner hoon — **code simple rakho.**
- Har important line par **Hinglish me chhota comment** likho (kya aur kyun).
- **Har step ke baad ruko**, bata do kya bana, aur mere confirm karne par
  aage badho.
- **Files:** `main.py`, `youtube.py`, `ai.py`, `db.py`, `filters.py`,
  `config.py`.
