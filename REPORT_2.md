# REPORT_2 — Institute v2 + voice/facts test (Step 5)

- Date: 2026-11-15 16:03
- Real knowledge file (`knowledge/zedking_info.md`) se values — koi hardcode value nahi.
- YouTube API call **0**, POST **0**. LLM sirf classification ke liye hoti hai — test me band hai (offline + deterministic).
- Har reply par automatic checks: markdown, glued word, internal word, promise (vaada), AI-jaisa phrase, em dash, third-person 'ZedKing ke ...', link count/domain, 280 char, comment ki language.

## 16 comments — decision + reply

| ID | Comment | Label | Reply | Checks |
|---|---|---|---|---|
| v2-01 | CCC course ki fees kitni hai? | institute_info | Hamare CCC course fee ₹6,000 hai. Full details yahan dekh sakte hain: https://zedking.in/ccc-computer-course | PASS |
| v2-02 | CCC course ki fees aur duration kitni hai? | institute_info | Hamare CCC wale course fees ₹6,000 hai aur duration 3 Months hai. Poori detail yahan dekhein: https://zedking.in/ccc-computer-course | PASS |
| v2-03 | Python course ki eligibility kya hai? | institute_info | Course ka naam likh do - list me se koi bhi ek. | PASS |
| v2-04 | Tally course kitne mahine ka hai? | institute_info | Kaun sa course chahiye - CCBA Accounting ya Financial Accounting? Course ka naam likh do. | PASS |
| v2-05 | digital marketing ki fees | institute_info | Kis course ki baat ho rahi hai? Naam likh do bas. | PASS |
| v2-06 | AI Digital Pro ki fees kitni hai? | institute_info | Hamare AI Digital Pro course - fee ₹35,000 lagti hai. Poori detail yahan dekhein: https://zedking.in/ai-digital-pro-course | PASS |
| v2-07 | Bitcoin trading course karwana? | institute_info | Hamari list me ye course nahi hai. Call karein: +91-9416111612. | PASS |
| v2-08 | Fire safety course ki eligibility? | institute_info | Ye jaankari abhi confirm nahi hai. Number: +91-9416111612. | PASS |
| v2-09 | Address kya hai institute ka? | institute_info | Call karein: +91-9416111612. Pata: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027, India. Admission yahan: https://zedking.in/admission | PASS |
| v2-10 | admission kaise le | institute_info | Call karo: +91-9416111612. Hamara address: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027, India. Admission form yahan: https://zedking.in/admission | PASS |
| v2-11 | फीस कितनी है? | institute_info | किस कोर्स के बारे में पूछ रहे हैं? कोर्स का नाम लिख दीजिए। | PASS |
| v2-12 | What is the duration of CCC? | institute_info | Our CCC course - it runs for 3 Months. Check full details here: https://zedking.in/ccc-computer-course | PASS |
| v2-13 | Which camera did you use? | video_question | (no reply) | PASS |
| v2-14 | Nice video bro | praise | Thanks for the love! | PASS |
| v2-15 | Bot ho kya? | asks_if_bot | (no reply) | PASS |
| v2-16 | Aap kahan rehte ho? | personal_question | (no reply) | PASS |

## Checks

| Check | Result |
|---|---|
| v2-01 label=institute_info | PASS |
| v2-01 reply checks | PASS |
| v2-01 fee value file se match (₹6,000) | PASS |
| v2-02 label=institute_info | PASS |
| v2-02 reply checks | PASS |
| v2-02 fee value file se match (₹6,000) | PASS |
| v2-02 duration value file se match (3 Months) | PASS |
| v2-03 label=institute_info | PASS |
| v2-03 reply checks | PASS |
| v2-03 course ka naam poochha (number nahi) | PASS |
| v2-04 label=institute_info | PASS |
| v2-04 reply checks | PASS |
| v2-04 course ka naam poochha (number nahi) | PASS |
| v2-05 label=institute_info | PASS |
| v2-05 reply checks | PASS |
| v2-05 course ka naam poochha (number nahi) | PASS |
| v2-06 label=institute_info | PASS |
| v2-06 reply checks | PASS |
| v2-06 fee value file se match (₹35,000) | PASS |
| v2-07 label=institute_info | PASS |
| v2-07 reply checks | PASS |
| v2-07 phone (aur koi number nahi) | PASS |
| v2-08 label=institute_info | PASS |
| v2-08 reply checks | PASS |
| v2-08 phone (aur koi number nahi) | PASS |
| v2-09 label=institute_info | PASS |
| v2-09 reply checks | PASS |
| v2-09 phone (aur koi number nahi) | PASS |
| v2-10 label=institute_info | PASS |
| v2-10 reply checks | PASS |
| v2-10 phone (aur koi number nahi) | PASS |
| v2-11 label=institute_info | PASS |
| v2-11 reply checks | PASS |
| v2-11 course ka naam poochha (number nahi) | PASS |
| v2-12 label=institute_info | PASS |
| v2-12 reply checks | PASS |
| v2-12 duration value file se match (3 Months) | PASS |
| v2-13 label=video_question | PASS |
| v2-13 reason=needs_owner | PASS |
| v2-13 koi reply nahi | PASS |
| v2-14 label=praise | PASS |
| v2-14 reply checks | PASS |
| v2-15 label=asks_if_bot | PASS |
| v2-15 reason=asks_if_bot | PASS |
| v2-15 koi reply nahi | PASS |
| v2-16 label=personal_question | PASS |
| v2-16 reason=personal_question | PASS |
| v2-16 koi reply nahi | PASS |
| owner_facts me fact = reply me fact | PASS |
| facts khali = needs_owner skip (no reply) | PASS |

**Total: 50/50 PASS**
