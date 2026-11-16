# REPORT_4 - INSTITUTE_LIVE_ON_PERSONAL (PROMPT 12, Step 5)

- Date: 2026-11-16 19:39
- **SIRF MOCK:** FakeYouTube + FakeLLM. Real YouTube API call **0**, real POST **0**. config.py ke defaults nahi badle (MODE=draft, INSTITUTE_MODE=True, CHANNEL_PROFILE=personal).
- Rule (main.py): institute reply LIVE tabhi jab (profile zedking) YA (INSTITUTE_LIVE_ON_PERSONAL=True), aur MODE=auto + --live dono bhi.

## 4 cases + guard

| Case | Profile | Flag | MODE | live | DB status | Post (mock) | Result |
|---|---|---|---|---|---|---|---|
| (a) | personal | False | auto | True | draft | 0 | PASS |
| (b) | personal | True | draft | True | draft | 0 | PASS |
| (c) | personal | True | auto | True | posted | 1 (mock) | PASS |
| (d1) | zedking | False | auto | True | posted | 1 (mock) | PASS |
| (d2) | zedking | False | draft | True | draft | 0 | PASS |
| guard | personal | False | auto | True | posted | 1 (mock) | PASS |

## Checks

- (a) personal + flag False + auto + live = draft, POST 0: PASS
- (b) personal + flag True + MODE=draft = draft, POST 0: PASS
- (c) personal + flag True + auto + live = posted (mock), db reply == post text: PASS
- (d) zedking pehle jaisa (auto+live=posted, draft=draft): PASS
- guard: non-institute reply personal par post ho sakta hai (purana behavior): PASS

**Result:** 11/11 checks PASS.

### Notes

- (c) ka 'post' FakeYouTube list me hua hai - real YouTube par kuch nahi gaya.
- Safeties untouched: validators, contact cap 10, link cap 15, live cap 3/run, delay 20-60s, STOP file, 24h cutoff.
- Step 4 (already_replied check): draft row 'done' NAHI hoti (db.already_done) - draft comment agli run me re-process hota hai, isliye flag ON ke baad purane drafts (24h ke andar wali) post ho payengi. 24h se purani draft too_old par permanently skip hogi.
- Default ab bhi safe: flag False = personal par institute reply hamesha draft.
