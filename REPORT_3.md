# REPORT_3 — Step 7 test (10 comments)

- Date: 2026-11-16 16:07
- **Draft mode:** sirf pipeline test — YouTube API call **0**, POST **0**. Har comment EK baar chala (loop nahi).
- Offline: LLM classification band (`ai._llm_classify_course -> None`) + FakeLLM.
- Real knowledge file (`knowledge/zedking_info.md`) se values.

## 10 comments — decision + reply

| id | comment | label | reply | checks |
|---|---|---|---|---|
| s7-01 | Ccc course ki fees? | institute_info | Hamare CCC course ki fee ₹6,000 hai. Poori detail: https://zedking.in/ccc-computer-course | PASS |
| s7-02 | CCC course ki fees aur duration kitna hai? | institute_info | Hamare CCC course ki fee ₹6,000 hai, duration 3 Months. Full details yahan dekh sakte hain: https://zedking.in/ccc-computer-course | PASS |
| s7-03 | Kaha par h centre ? | institute_info | Hamara centre yahan hai: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027. Call: +91-9416111612. Admission form yahan: https://zedking.in/admission | PASS |
| s7-04 | Centre ka name ? | institute_info | Zed-King Group of Institute (ZedKing Institute), Kaithal me hai. Course ya fees ke baare me bata do. | PASS |
| s7-05 | Editing vaigara ka koi course hota h yaha par? | institute_info | Aap Designing & Publishing, Web Designing & Multimedia (CCWD) ya NIELIT A Level ke baare me pooch rahe ho? | PASS |
| s7-06 | Course ka naam kya hai? | institute_info | Kaunsa course jaanna chahte ho? Kuch popular courses: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. Sab courses: https://zedking.in/courses | PASS |
| s7-07 | What is the fee of Python course? | institute_info | Which course are you asking about? Popular ones: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. See all courses: https://zedking.in/courses | PASS |
| s7-08 | कंप्यूटर कोर्स की फीस कितनी है? | institute_info | कौन सा कोर्स जानना चाहते हैं? कुछ लोकप्रिय कोर्स: NIELIT O Level, NIELIT A Level, Office Automation, Accounting & Publishing. सभी कोर्स: https://zedking.in/courses | PASS |
| s7-09 | Bitcoin trading course karwana? | institute_info | Ye course hamari list me nahi hai abhi. Course list ke liye call karein: +91-9416111612. | PASS |
| s7-10 | Admission kaise le? | institute_info | Centre yahan hai: Kaithal - Pundri - Karnal Rd, near New Bus Stand, opp. Hanuman Vatika, Friends Colony, Kaithal, Haryana 136027. Hamara number: +91-9416111612. Admission: https://zedking.in/admission | PASS |

## Checks (spec Step 7)

- Fee replies me sahi phrasing (ki fee / fee is / की फीस): PASS
- Kisi reply me 'wale' nahi; template ka ASCII ' - ' dash nahi (address ka ' - ' = file ka data, wo alag): PASS
- Reply language comment ki language jaisi: PASS
- Address me 'India' nahi: PASS
- institute_name sahi (naam + city): PASS
- Jahan matching course hai wahan galat 'list me nahi' nahi: PASS
- Devanagari reply me glued shabd nahi (checker Devanagari bhi pakadta hai): PASS

**Result:** 86/86 checks PASS.

### Notes

- `What is the fee of Python course?` / `कंप्यूटर कोर्स की फीस कितनी है?` me specific course match nahi hota (ek hi weak candidate / koi nahi) — bot clarification deta hai, fee value guess NAHI karta (policy rule).
- `Bitcoin trading course karwana?` = hamari list me sach me nahi — wahan sirf wahi 'list me nahi' sahi hai.
- **' - ' check ka sach:** reply me address FILE ka exact hai (`zedking_info.md` contact page: `Kaithal - Pundri - Karnal Rd, ...` — usme ASCII ' - ' hai, template se nahi). Test me `wo_addr = reply.replace(address, "")` karke sirf template wale hisse par check lagta hai, isliye address ka ' - ' count nahi hota. `reply_checks._DASH_RE` sirf em/en dash (— –) pakadta hai — ASCII ' - ' par wo lagta hi nahi.
