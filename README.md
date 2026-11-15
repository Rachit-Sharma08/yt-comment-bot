# YouTube Comment Auto-Reply Bot

Local PC par chalne wala Python bot. Apne YouTube channel ke naye comments laata hai
(official **YouTube Data API v3** se), unhe video context ya institute knowledge ke
hisab se **reply** likhta hai (LLM: Groq → Gemini fallback), aur reply post karta hai.

Default **`draft`** mode hai — reply sirf `bot.db` me save hoti hain, YouTube par
kuch nahi jaata jab tak tum `MODE=auto` + `--live` jaan-bujhkar na karo.

---

## Flow

```
        ┌───────────────────────────────────────────────┐
        │ YouTube Data API v3  (fetch_new_comments)     │
        │ apne channel ke comments, 50 max per run       │
        └───────────────────────┬───────────────────────┘
                                │ naye comments
                                ▼
        ┌───────────────────────────────────────────────┐
        │ filters.should_skip  + emoji check            │──▶ SKIP (db me reason save,
        │ empty / abusive / spam-link / criticism /      │    reply nahi)
        │ injection / personal question / neg-emoji      │
        └───────────────────────┬───────────────────────┘
                                │ bache hue comments
                                ▼
        ┌───────────────────────────────────────────────┐
        │ intent.classify_comment                        │
        │ spam · criticism · asks_if_bot · praise ·     │──▶ "bot ho kya / AI hai?"
        │ personal_question · institute_info · video_q   │    → SKIP (owner khud de)
        └───────────────┬───────────────────┬───────────┘
                        │                   │
        praise ─────────┘                   │ video ka factual sawaal
            │                              │ (camera/mic/editing/location)
            ▼                              ▼
   ┌──────────────────────┐   ┌────────────────────────────────────┐
   │ templates.praise()   │   │ video_notes/<id>.md → owner_facts.md │
   │ (voice_samples ka    │   │ fact mila → 1-line casual reply      │
   │  andaaz, LLM nahi)   │   │ fact nahi → SKIP (needs_owner)       │
   └──────────────────────┘   └────────────────────────────────────┘
                        │
                        │ institute_info
                        ▼
   ┌──────────────────────────────────────────────────────────┐
   │ knowledge.course_records() (41 courses, structured)      │
   │ + field detect (fee/duration/eligibility/mode/cert)      │
   │ → TEMPLATE reply ("Hamare CCC course fee ... hai")       │
   │ → ambiguous → clarification · list me nahi → phone reply  │
   │ LLM sirf CLASSIFY karta hai (rule fail ho tabhi, temp 0) │
   └───────────────────────┬──────────────────────────────────┘
                           ▼
                  ┌───────────────────────────────────┐
                  │ Validators (ai.py + reply_checks)  │
                  │ URL/phone/secret/first-person/     │
                  │ internal-word/promise/AI-phrase/    │
                  │ em-dash/third-person + grounding    │
                  └───────────────┬───────────────────┘
                                  ▼
                  ┌───────────────────────────────────┐
                  │ MODE=draft → sirf bot.db me save   │──▶ review.py --drafts / --owner
                  │ MODE=auto  → YouTube par post      │    (live: 20-60s gap)
                  └───────────────────────────────────┘
```

---

## Features

- **Official API only** — koi scraping ya browser automation nahi, sirf YouTube Data API v3 (OAuth).
- **4 reply sources** — emoji template, keyword trigger, praise template (voice samples), normal LLM.
- **Institute replies = sirf templates** — 41 courses ka structured record (`knowledge.course_records()`),
  fee/duration/eligibility/mode/certificate values file se **hubahu**; "hum/hamare" awaaz me.
  LLM sirf **classify** karta hai (rule fail ho tabhi, temperature 0, JSON output).
- **Koi jhootha vaada nahi** — "dekh ke bata hoon" / "I'll check and let you know" jaisa promise
  validator reply discard kar deta hai.
- **Owner facts** — camera/mic/editing/location/music/upload-time ka jawab sirf
  `video_notes/<id>.md` ya `knowledge/owner_facts.md` se. Na mile to reply nahi
  (`needs_owner`) — owner khud jawab de.
- **"Bot ho kya / AI hai?" par reply nahi** — `asks_if_bot` skip (owner khud bolega).
- **3 languages** — Roman Hinglish, English, Devanagari Hindi. Reply **comment ki hi language + script** me hoti hai.
- **Hallucination ke khilaf validators** — reply me koi fee/phone/address/link sirf tab jata hai jab wo knowledge file me **hubahu** likha ho.
- **AI-jaise phrases + em dash + third-person "ZedKing ke ..."** reply me nahi (discard).
- **Link whitelist** — sirf `zedking.in` ke links, aur sirf daily cap tak.
- **Prompt-injection safe** — comment "untrusted data" maana jaata hai; instruction-wali comments skip.
- **Skip rules** — abuse, spam-link, criticism, personal question, negative emoji, empty comment.
- **Kill switch** — `STOP` file banate hi bot 1 second me band.
- **Quota-safe** — local 8,000 units/day cap (YouTube ka 10,000), quota 403 par aaj ke liye ruk jaata hai.
- **Draft-first** — default me koi post nahi; review karke hi live kiya jaata hai.
- **Test suite** — poora mock layer (real API call 0), failure/loop/stability, real-LLM quality, review stats, Windows runner.

---

## Folder structure

```
yt-bot/
├── main.py              # ek run / loop, lock, quota, STOP kill switch, post logic
├── config.py            # saari settings + .env se API keys (defaults yahin)
├── youtube.py           # sirf official YouTube Data API v3 (OAuth, comments + replies)
├── ai.py                # reply generation (Groq → Gemini) + saare validators
├── pipeline.py          # comment → reply ka EK path (main aur tests dono yahi use karte hain)
├── intent.py            # comment ka label (rules + LLM fallback)
├── filters.py           # spam/abuse/criticism/injection skip + emoji + markdown strip
├── triggers.py          # keyword → canned reply (triggers.json se)
├── triggers.json        # trigger words + unki replies
├── knowledge.py         # knowledge/zedking_info.md → chunks, search, allowed URLs
├── templates.py         # fixed templates (clarify / unknown / contact / link)
├── db.py                # SAARA database code (SQLite) — baad me Supabase shift easy
├── review.py            # drafts / --today / --stats
├── mock_youtube.py      # FakeYouTube + FakeLLM (tests ke liye, real API call nahi)
├── reply_checks.py      # reply ke automatic checks (markdown/glued/links/language...)
├── report_utils.py      # OVERNIGHT_REPORT.md ke sections
├── run_bot.bat          # Windows runner (loop mode; exit 3 = no restart)
├── stop_bot.bat         # kill switch ON  (STOP file)
├── resume_bot.bat       # kill switch OFF (STOP file delete)
├── knowledge/
│   ├── zedking_info.md  # 41+ courses ka verified data (fee/duration/eligibility/URL)
│   ├── owner_facts.md   # owner ki apni jaankari (camera/mic/editing...) — khali = reply nahi
│   ├── voice_samples.md # casual reply ke style examples (few-shot)
│   └── CHECKLIST.md     # knowledge file kaise update karein
├── test_e2e.py          # 43 comments, full pipeline (sirf mock)
├── test_failures.py     # 11 failure scenarios (quota/token/lock/STOP...)
├── test_loop.py         # loop stability (repeat, backoff, duplicate)
├── test_institute_v2.py # 16 institute/facts comments + 50 checks (real knowledge file)
├── test_real_llm.py     # 12 real LLM calls — reply quality
├── test_review.py       # review --stats / --today / --owner
├── test_runner.py       # run_bot.bat exit-code logic
├── test_institute.py    # institute reply path (pipeline ke saath)
├── test_ai.py, test_all.py, test_space.py
├── REPORT_2.md          # Step 5 (institute v2) ka report
├── OVERNIGHT_REPORT.md  # test results ka report
├── PRESENTATION_NOTES.md # demo/presentation script
├── WINDOWS_RUN.md       # Windows chalaane + autostart ke steps
└── AGENTS.md            # project ke rules (policy, coding style, awaaz + facts)
```

---

## Setup

### 1) Virtual environment (Windows, PowerShell)

```powershell
cd D:\yt-bot
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2) `.env` banao aur bharo

```powershell
copy .env.example .env
notepad .env
```

`.env` me sirf ye keys hain (koi aur nahi):

| Key | Kaam |
|---|---|
| `GROQ_API_KEY` | primary LLM (https://console.groq.com) |
| `GEMINI_API_KEY` | fallback LLM (https://aistudio.google.com) |
| `MODE` | `draft` (default) ya `auto` |
| `CHANNEL_PROFILE` | `personal` (default) ya `zedking` |
| `INSTITUTE_MODE` | `true` (default) ya `false` |

### 3) Google OAuth (YouTube Data API v3)

1. [Google Cloud Console](https://console.cloud.google.com/) → naya project
2. **APIs & Services → Library** → **YouTube Data API v3** → Enable
3. **OAuth consent screen** → External → apna Google account add karo (test user)
4. **Credentials → Create Credentials → OAuth client ID** → Application type: **Desktop app**
5. JSON download karke naam `client_secret.json` rakho aur repo root me rakho
6. Pehli baar login:

```powershell
venv\Scripts\python.exe main.py --once
```

Browser khulega → "Allow" karo → `token.json` ban jayega (agle baar browser nahi khulega).

> Token expire/revoke ho gaya? `token.json` delete karo aur wahi command dobara chalao.
> Bot is par exit code **3** deta hai aur apne aap restart **nahi** karta.

`client_secret.json`, `token.json`, `.env` aur `bot.db` `.gitignore` me hain — kabhi commit nahi hone chahiye.

### 4) Apni jaankari bharo (owner facts)

`knowledge/owner_facts.md` kholo aur apni asli jaankari bharo — camera, mic, editing
software, shehar, music, upload time. **Jawab khali chhodne ka matlab** bot us sawaal
par reply nahi karega (`needs_owner`) — wo comments `review.py --owner` me dikhte hain,
tum khud jawab de sakte ho.

`knowledge/voice_samples.md` me reply ka casual andaaz already likha hai (wahi style
LLM ko diya jaata hai) — usse apni pasand ke hisaab se badal sakte ho.

---

## Modes

| Command / setting | Kya hota hai |
|---|---|
| `main.py --once` | ek run (comments fetch → replies → save/post) |
| `main.py --loop` | continuous — har 5 min (±30s) naye comments check |
| `main.py --loop --live` | live posting (sirf `MODE=auto` ke saath post karta hai) |
| `main.py --mock` | **FakeYouTube** — real YouTube API call nahi (tests) |
| `main.py --mock --mock-llm` | fixed fake LLM replies bhi (bina `--mock` ke block) |
| `MODE=draft` (default) | replies sirf db me save — YouTube par kuch nahi |
| `MODE=auto` | replies post hoti hain (aur `--live` chahiye) |
| `CHANNEL_PROFILE=personal` (default) | institute replies **hamesha** draft me |
| `CHANNEL_PROFILE=zedking` | institute replies live post ho sakti hain |
| `INSTITUTE_MODE=false` | institute questions skip (reply nahi) |

---

## Safety

- **Sirf official API** — scraping, browser automation, unofficial tricks bilkul nahi.
- **Draft-first** — default me kuch post nahi hota; live jaan-bujhkar on karo.
- **Kill switch** — `STOP` file (ya `stop_bot.bat`) bante hi bot band, pending post bhi nahi.
- **Caps** — 10 replies per run (live mode me 3), 8,000 units/day quota (YouTube 10,000),
  40 emoji replies/day, 10 contact (phone) replies/day, 15 link replies/day.
- **Delay** — do post ke beech random 20–60 sec; ek jaisa reply repeat nahi hota.
- **Validators** — URL/phone/secret/personal-claim/internal-word reply se phenke; institute facts
  knowledge chunk me grounded hone ke bina reply discard.
- **Apne channel ke comments** par kabhi reply nahi.
- **Prompt injection** — comment ka text untrusted data hai, uske instructions follow nahi hote.
- **No jhooth** — video context me jo nahi hai, wo nahi bola jaata ("dekh ke bataunga" wala reply).
- **Token expire** par exit code 3 + message, auto restart nahi.
- **Secrets** — keys kabhi log/print/commit nahi hoti. User data minimal hai:
  sirf comment id, video id, comment text, reply, status, time.
- **Log** — `bot.log` me comment ka sirf 100 char, keys kabhi nahi.

---

## Tests (sab mock, koi real YouTube call nahi)

```powershell
venv\Scripts\python.exe test_e2e.py          # 43 comments, full pipeline
venv\Scripts\python.exe test_failures.py     # 11 failure scenarios
venv\Scripts\python.exe test_loop.py         # loop stability
venv\Scripts\python.exe test_institute_v2.py # 16 comments + 50 checks (real knowledge file)
venv\Scripts\python.exe test_review.py       # review --stats / --today / --owner
venv\Scripts\python.exe test_runner.py       # run_bot.bat exit codes
venv\Scripts\python.exe test_real_llm.py     # 12 real LLM calls (quality check)
```

Har test apna result `OVERNIGHT_REPORT.md` me apne section me likhta hai
(`REPORT_2.md` institute v2 ka report hai).

---

## Review + Windows

```powershell
venv\Scripts\python.exe review.py --drafts   # draft replies poora text
venv\Scripts\python.exe review.py --today    # aaj ki rows
venv\Scripts\python.exe review.py --stats    # total + status/reason counts
venv\Scripts\python.exe review.py --owner    # needs_owner + asks_if_bot (owner jawab de)
```

Windows par chalane aur autostart (Task Scheduler/Startup folder) ke steps:
[WINDOWS_RUN.md](WINDOWS_RUN.md). `run_bot.bat` double-click karke chalao —
loop mode, exit 3 (token expire) par restart nahi karta.
