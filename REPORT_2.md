# REPORT_2 — Institute v2 + voice/facts test (Step 5)

- Date: 2026-11-16 16:07
- Real knowledge file (`knowledge/zedking_info.md`) se values — koi hardcode value nahi.
- YouTube API call **0**, POST **0**. LLM sirf classification ke liye hoti hai — test me band hai (offline + deterministic).
- Har reply par automatic checks: markdown, glued word, internal word, promise (vaada), AI-jaisa phrase, em dash, third-person 'ZedKing ke ...', link count/domain, 280 char, comment ki language.

## 16 comments — decision + reply

| ID | Comment | Label | Reply | Checks |
|---|---|---|---|---|
| v2-01 | CCC course ki fees kitni hai? | institute_info | CCC course ki fee ₹6,000 hai. Full details yahan dekh sakte hain: https://zedking.in/ccc-computer-course | PASS |
| v2-02 | CCC course ki fees aur duration kitni hai? | institute_info | CCC course ki fee ₹6,000 hai, duration 3 Months. Poori detail: https://zedking.in/ccc-computer-course | PASS |
| v2-03 | Python course ki eligibility kya hai? | institute_info | Kaunsa course jaanna chahte ho? Kuch popular courses: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. Sab courses: https://zedking.in/courses | PASS |
| v2-04 | Tally course kitne mahine ka hai? | institute_info | Kaun sa course chahiye: CCBA Accounting ya Financial Accounting? Course ka naam likh do. | PASS |
| v2-05 | digital marketing ki fees | institute_info | Kaun sa course chahiye? Popular: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. Sab courses dekh lo: https://zedking.in/courses | PASS |
| v2-06 | AI Digital Pro ki fees kitni hai? | institute_info | Hamare AI Digital Pro course ki fee ₹35,000 hai. Poori detail: https://zedking.in/ai-digital-pro-course | PASS |
| v2-07 | Bitcoin trading course karwana? | institute_info | Hamari list me ye course nahi hai. Call karein: +91-9416111612. | PASS |
| v2-08 | Fire safety course ki eligibility? | institute_info | Ye jaankari abhi confirm nahi hai. Number: +91-9416111612. | PASS |
| v2-09 | Address kya hai institute ka? | institute_info | Hamara centre yahan hai: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027. Call: +91-9416111612. Admission form yahan: https://zedking.in/admission | PASS |
| v2-10 | admission kaise le | institute_info | Centre yahan hai: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027. Hamara number: +91-9416111612. Admission: https://zedking.in/admission | PASS |
| v2-11 | फीस कितनी है? | institute_info | कौन सा कोर्स पूछ रहे हैं? कुछ लोकप्रिय कोर्स: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. सभी कोर्स देखें: https://zedking.in/courses | PASS |
| v2-12 | What is the duration of CCC? | institute_info | Our CCC course duration is 3 Months. You can see full details here: https://zedking.in/ccc-computer-course | PASS |
| v2-13 | Which camera did you use? | video_question | (no reply) | PASS |
| v2-14 | Nice video bro | praise | Thanks a lot, means a lot 🙏 | PASS |
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
