# Presentation Notes — YouTube Comment Auto-Reply Bot (Demo Script)

## 1. Bot kya hai (30 sec intro)
Yeh local PC par chalne wala Python bot hai jo mere YouTube channel ke naye comments fetch karta hai (official YouTube Data API v3 se), video ke context (title, description, transcript/notes) ke hisaab se relevant reply likhta hai (LLM: Groq primary + Gemini fallback), aur reply post karta hai. Default **draft mode** hai — kuch YouTube par nahi jaata jab tak main `MODE=auto` + `--live` jaan-bujhkar na karun.

## 2. Bot kya NAHI karta (safety first)
- **Koi scraping/browser automation nahi** — sirf official YouTube Data API v3 (OAuth).
- **Koi real post draft mode me nahi** — default `MODE=draft` me reply sirf `bot.db` me save hoti hain.
- **Apne khud ke comments par reply nahi** — channel ke malik ke comments skip.
- **Spam jaisa behavior nahi** — 20–60 sec random gap, daily caps, quota limit 8000/10000 units.
- **Jhooth/vaada nahi** — jo fact `knowledge/owner_facts.md` ya `video_notes/` me nahi hai, us par reply nahi (`needs_owner` skip) aur kabhi "dekh ke bataunga" jaisa vaada nahi.
- **Fee/phone/address/link sirf knowledge file se** — validator check karta hai, warna reply discard.
- **Prompt injection safe** — comment "untrusted data" hai, uske instructions follow nahi hote.
- **Kabhi pehle person me apne baare me nahi bolta** — institute channel par "hum/hamari team" awaaz, personal par bhi koi personal claim nahi.

## 3. Mock mode me demo kaise karein (zero API calls, zero risk)
```bat
venv\Scripts\python.exe main.py --mock           # FakeYouTube (real API call nahi)
venv\Scripts\python.exe main.py --mock --mock-llm # Fixed fake LLM replies bhi
```
Ye dono flags `mock_youtube.py` ka FakeYouTube + FakeLLM layer activate karte hain. Real YouTube/Groq/Gemini call **bilkul nahi hoti**. Terminal me "MOCK mode: FakeYouTube — real YouTube API call nahi hogi" dikhega. Summary me `Posted (auto mode) : 0` aur `Draft save` dikhega.

## 4. Real flow safely demo kaise karein (draft review)
```bat
venv\Scripts\python.exe main.py --once           # Ek run, MODE=draft (default)
venv\Scripts\python.exe review.py --drafts       # Poore draft replies padho
venv\Scripts\python.exe review.py --today        # Aaj ki saari rows
venv\Scripts\python.exe review.py --stats        # Total + status/reason counts
```
Koi post YouTube par nahi jaati. `bot.db` me draft rows banti hain — `review.py --drafts` se poora comment + reply text dekh sakte ho. Jab satisfy ho, tabhi `.env` me `MODE=auto` set karke `--live` chalana.

## 5. Exact commands (copy-paste ready)
| Kaam | Command |
|---|---|
| Ek run (draft) | `venv\Scripts\python.exe main.py --once` |
| Loop chalu (draft) | `venv\Scripts\python.exe main.py --loop` |
| Loop live (real post) | `venv\Scripts\python.exe main.py --loop --live` *(needs MODE=auto)* |
| Mock demo | `venv\Scripts\python.exe main.py --mock` |
| Mock + fake LLM | `venv\Scripts\python.exe main.py --mock --mock-llm` |
| Drafts dekhna | `venv\Scripts\python.exe review.py --drafts` |
| Aaj ka log | `venv\Scripts\python.exe review.py --today` |
| Stats | `venv\Scripts\python.exe review.py --stats` |
| Kill switch ON | `stop_bot.bat` (ya `echo. > STOP`) |
| Kill switch OFF | `resume_bot.bat` (ya `del STOP`) |
| Autostart shortcut | `Win+R → shell:startup` me `run_bot.bat` ka shortcut |

## 6. Logs / drafts kahan milenge
- `bot.log` — saari activity (comment 100 char tak, keys kabhi nahi).
- `bot.db` — SQLite: replies, drafts, quota counter, video cache. `review.py` se query karo.
- `bot.lock` — single-instance lock (30 min stale = auto-free).
- `STOP` file — kill switch marker (repo folder me).
- `token.json` — OAuth token (expire ho to delete + dobara login).

## 7. Kill switch (turant band)
Repo folder me `STOP` naam ki file banaate hi bot **~1 second me band** ho jaata hai — pending post bhi nahi hota.
```bat
stop_bot.bat      # STOP file bana deta hai
resume_bot.bat    # STOP file hata deta hai (ya `del STOP`)
```
Loop ke andar har ~1 sec me check hota hai. `run_bot.bat` bhi exit code 0 de ke saaf nikalta hai.

## 8. Safety caps (numbers yaad rakho)
| Cap | Value | Kahan |
|---|---|---|
| Replies per run (draft/auto) | 10 | `MAX_REPLIES_PER_RUN` |
| Replies per run (--live) | 3 | `MAX_REPLIES_PER_RUN_LIVE` |
| Daily YouTube quota (local) | 8000 units | `QUOTA_LIMIT` (YouTube limit 10000) |
| Reply post cost | 50 units | YouTube API |
| Emoji replies/day | 40 | `MAX_EMOJI_REPLIES_PER_DAY` |
| Contact/phone replies/day | 10 | `MAX_CONTACT_REPLIES_PER_DAY` |
| Link replies/day | 15 | `MAX_LINK_REPLIES_PER_DAY` |
| Gap between replies | 20–60 sec random | `REPLY_DELAY_MIN/MAX_SEC` |
| Check interval | 5 min ± 30 sec | `CHECK_INTERVAL_MIN` |
| Comment age cutoff | 24 hours | `MAX_COMMENT_AGE_HOURS` |

## 9. Demo talking points (kya bolna hai)
- "Default draft mode hai — aapko kuch bhi post nahi hua dikhega."
- "Mock mode me real API call zero — safe demo ke liye best."
- "Validator check: fee/phone/link sirf knowledge file se, warna reply discard."
- "Kill switch: ek file (`STOP`) se poora bot turant band."
- "Quota 8000/10000 — channel ka quota kabhi khatam nahi hone deta."
- "Language matching: Roman Hinglish comment → Roman Hinglish reply, Devanagari → Devanagari."
- "Institute replies sirf `CHANNEL_PROFILE=zedking` par live post hoti hain."
- "`asks_if_bot` skip rule: 'are you a bot?' comments ko main khud jawab dunga."

## 10. Known limitations (honest disclosure)
- **Sirf top-level comments** — replies-to-replies (threaded) abhi handle nahi hote.
- **24h cutoff** — purane comments par reply nahi karta (fresh conversation focus).
- **Video notes file optional** — `video_notes/<video_id>.md` ho to context better hota hai.
- **Token expire** par bot exit code 3 deta hai, auto-restart nahi karta (manual login chahiye).
- **Single instance lock** — `bot.lock` se ek hi bot chalega; dusra instance turant nikal jayega.
- **LLM cost** — Groq free tier + Gemini free tier use hote hain, paid plan chahiye scale ke liye.

## 11. Next steps (roadmap)
- Threaded replies support (reply-to-reply).
- Multi-channel support (ek hi bot se multiple channels).
- Better intent classification (fine-tuned model ya few-shot).
- Dashboard/WEB UI for draft review (abhi CLI `review.py`).
- Supabase migration (abhi SQLite `db.py` me hai, schema ready).
- Scheduled posting (time-window based posting).

## 12. Troubleshooting one-liners
| Problem | Fix |
|---|---|
| `Token expire ho gaya` (exit 3) | `del token.json` → `venv\Scripts\python.exe main.py --once` → browser login |
| `Ek aur instance chal raha hai` | Pehle wala band karo ya `bot.lock` 30 min purana hone ka wait karo |
| `STOP file mila` | `resume_bot.bat` chalao ya `del STOP` |
| `403 quotaExceeded` | Aaj quota khatam — kal khud chalega |
| `Quota aaj: 8000/8000` | Local limit — config `.env` me `QUOTA_LIMIT` badhao (max 10000) |
| Bot chal raha par reply nahi | `.env` me `MODE` check karo — `draft` me sirf db me save hota hai |
| `Unknown flag` error | Sirf `--once --loop --live --mock --mock-llm` allowed hain |