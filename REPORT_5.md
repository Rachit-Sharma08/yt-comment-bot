# REPORT_5 — Roman Hinglish chipke shabd ka bug (Prompt 14)

- Date: 2026-11-20
- Mode: draft (default) — YouTube API call **0**, POST **0**.
- Bot **nahi chalaya**; `.env`/`token.json`/`client_secret.json` **nahi khule**.
- Defaults **nahi badle** (`MODE=draft`, `INSTITUTE_MODE=True`, `CHANNEL_PROFILE=personal`).

---

## Bug

`test_real_llm.py` ke `llm-10` ("Digital marketing course ki duration kitni hai?")
me reply aaya:

> "Hamare Digital Marketing (DMA) course ki fee ₹15,000 hai **aurduration** 6 Months hai."

`aurduration` chipka hua tha (space gayab), magar checker ne PASS kar diya.

---

## Step 1 — Root cause

Chipka text **do jagah se** aa sakta hai:

1. **Reply assembly** — `templates.py:course_reply` (line 109) — `config.py:380-396`
   ke `COURSE_COMBINED_TEMPLATES` (fee+duration ek saath) aur
   `templates.py:136-138` ke field-join (`" ".join(...)`) se.
2. **LLM free-text path** — `ai.py:make_reply` (line 241) — model khud text likhta hai.

**Scan result:** config ke **saare** template strings par `\S\{` (placeholder se
pehle space gayab) aur `\}\S` (placeholder ke baad letter) check kiya —
**koi missing-separator template NAHI mila**. 18 Roman/English combos render
karke dekhe — **0 glued**. Yaani current tree me koi toota template nahi hai;
glued text LLM free-text path se aa sakta hai, aur checker usko **sirf tab** pakadta
jab glued word 10+ char ka ho (jaise `aurduration`) — **chhote glued shabd**
(jaise `haiaur`, 6 char) **slip** jaate the.

**Asli gap:** `reply_checks.py` me Roman Hinglish/English ke liye auto-dictionary
wala glued check **nahi tha** — sirf Devanagari ke liye tha (`_dev_words`/`_dev_glued`).

**Saath hi ek aur asli bug mila (Step 4):** `ai.py:_asked_fields` me generic
"kitni/kitna" ko **fee field** ki tarah gin liya jaata tha. Isliye
"duration kitni hai?" me `kitni` ne fee bhi jod diya → reply me fee + duration
**dono** aa jaate the (jabki sirf duration pucha gaya tha).

---

## Step 2 — Saare combinations print kiye

18 Roman Hinglish + English combos (fee / duration / eligibility / mode /
certificate / fee+duration / fee+eligibility / duration+eligibility /
fee+duration+eligibility) render karke glued check chalaya:

```
TOTAL rendered: 18 | GLUED replies: 0
```

Koi template gluing nahi karta — templates saaf hain. (Fee+duration Roman
Hinglish bhi "hai aur duration" ke saath sahi space aata hai.)

---

## Fix 1 — `ai.py:_asked_fields` (Step 4)

Generic `kitni/kitna/kitne` (matra shabd) ko alag field jodne se roka:
jab comment me explicit field-naam (fee/duration/...) ho to **sirf wahi** field;
generic "kitni" akela ho to fee; kuch na ho to default dono.

| Comment | Pehle | Ab |
|---|---|---|
| "duration kitni hai?" | `[fee, duration]` ❌ | `[duration]` ✅ |
| "fees kitni hai?" | `[fee, duration]` ❌ | `[fee]` ✅ |
| "fees aur duration kitna hai?" | `[fee, duration]` | `[fee, duration]` ✅ |
| "kitne mahine ka hai?" | `[duration]` | `[duration]` ✅ |

Real-LLM `llm-10` ab: **"course ki duration 6 Months hai"** — fee nahi joda gaya.

---

## Fix 2 — `reply_checks.py` Roman/English auto-dictionary glued check

Devanagari jaisa hi `_en_words()` (config ke saare template shabd se auto-build)
+ `_en_glued(tok)` (word-break DP: token 2+ dictionary shabd me toota = glued).
`_glued_hits` me juda.

| Reply word | Result |
|---|---|
| `aurduration` | **FAIL (glued)** ✅ |
| `haiaur` | **FAIL (glued)** ✅ |
| `kifees` | **FAIL (glued)** ✅ |
| `feeRs` (case) | **FAIL (glued)** ✅ |
| `Marketingcourse` | **FAIL (glued)** ✅ |
| `duration` | PASS (false positive nahi) ✅ |
| `eligibility` | PASS ✅ |
| `certificate` | PASS ✅ |
| `admission` | PASS ✅ |
| `youtube` / `whatsapp` | PASS (legit compound) ✅ |

Poora reply: "…fee ₹15,000 hai **aurduration** 6 Months hai." → ab
`glued_word: ['aurduration']` FAIL hota hai.

---

## Step 3 — Checks jode

- `test_step7.py`: +7 glued unit checks + 3 Step-4 field checks → **96/96 PASS**.
- `test_real_llm.py`: glued unit checks (API keys ke bina bhi chalte hain) →
  **12/12** cases, glued unit **0 fail**, hard fail **0**.

---

## Step 4 — Sirf-duration / sirf-fee / dono

| Comment | Reply me |
|---|---|
| sirf duration puchhe | sirf duration ✅ |
| sirf fee puchhe | sirf fee ✅ |
| dono puchhe | dono ✅ |

Real-LLM `llm-10` (sirf duration) ne ab sirf duration diya — fee nahi.

---

## Step 5 — Read-only (personal channel, camera comment)

`pipeline.py:22 handle_comment` → pehle `intent.classify_comment` → label
`video_question` (camera owner-fact). Phir `pipeline.py:60` —
`ai.owner_question_field("Bhai ye vlog kis camera se shoot kiya?")` → `"camera"`.
`pipeline.py:62-73` — pehle `video_notes/<id>.md`, phir `knowledge/owner_facts.md`
se fact dhoondta hai. Fact **na mile** to `pipeline.py:73` →
`return label, None, [], "needs_owner"` — **reply post NAHI hoga**, db me
`skipped / needs_owner` save hota hai (main.py:252-259).

`test_real_llm.py` ke `llm-01..06` **asli pipeline (pipeline.py/main.py) se NAHI
jaate** — wo seedha `ai.make_reply(VIDEO_TITLE, VIDEO_CONTEXT, text)` bulatte hain
(`test_real_llm.py:137-139`, `_ask` me `kind == "video"`). `kind == "institute"`
wale (`llm-09..12`) seedha `ai.answer_institute` bulatte hain (line 140-141) —
pipeline se nahi. Matlab ye 12 cases **pipeline ka darshak nahi** hain; unke liye
`test_step7.py` / `test_institute_v2.py` / `test_e2e.py` asli path chalate hain.

---

## Tests (sab pass)

| Test | Result |
|---|---|
| `test_step7.py` | **96/96** PASS |
| `test_institute_v2.py` | **50/50** PASS |
| `test_e2e.py` | 43 comments, 20 replies, **20/20** checks, 0 decision mismatch |
| `test_failures.py` | **11/11** scenarios PASS |
| `test_real_llm.py` | **Glued unit checks 0 fail**; hard-fail cases = `no_reply` live-LLM flakiness (ke liye LLM fail, deterministic tests pass) |

---

## Files badle

- `ai.py` — `_asked_fields` generic "kitni" fix (+ purana duplicate function hatao).
- `reply_checks.py` — `_EN_GLUED_OK` / `_en_words()` / `_en_glued()` + `_glued_hits` me juda.
- `test_step7.py` — Roman glued + Step-4 checks.
- `test_real_llm.py` — Roman glued unit checks (keys ke bina bhi).
- `REPORT_5.md` — ye report.

**Na kiya:** `run_bot.bat` me koi change nahi, koi POST nahi, secrets nahi khule,
git push nahi.
