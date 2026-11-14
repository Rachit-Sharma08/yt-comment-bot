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
- **Reply ki language comment ki language jaisi hogi** — Devanagari Hindi ho to
  Devanagari Hindi, Roman Hinglish ho to Roman Hinglish, English ho to English.
- **Jo jaankari video context me nahi hai wo andaze se nahi bolni** — na pata
  ho to comment ki language me bolo ki dekh ke batata hoon.

## CODING STYLE (mujhe seekhna hai)

- Mai beginner hoon — **code simple rakho.**
- Har important line par **Hinglish me chhota comment** likho (kya aur kyun).
- **Har step ke baad ruko**, bata do kya bana, aur mere confirm karne par
  aage badho.
- **Files:** `main.py`, `youtube.py`, `ai.py`, `db.py`, `filters.py`,
  `config.py`.
