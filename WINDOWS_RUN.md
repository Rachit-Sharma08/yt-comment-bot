# Windows par bot chalana (run + autostart)

> Yahan sab kuch **manually** karte hain — maine computer par koi Task Scheduler
> entry ya startup service **register nahi ki hai**. Neeche ke steps khud follow karo.

---

## 1. Quick start

```
:: ek hi baar (draft mode - koi post nahi)
venv\Scripts\python.exe main.py --once

:: chalu (loop) - band karne ke liye Ctrl+C
venv\Scripts\python.exe main.py --loop

:: asli post (sirf jab .env me MODE=auto ho)
venv\Scripts\python.exe main.py --loop --live
```

`.env` me `MODE` default **`draft`** hai — matlab reply sirf database me save hoti hain,
YouTube par kuch nahi jaata. Asli post ke liye `.env` me `MODE=auto` **aur** `--live` dono chahiye.

---

## 2. Windows runner (.bat files)

| File | Kya karta hai |
|---|---|
| `run_bot.bat` | `main.py --loop` chala hai (loop mode). Extra args pass hote hain: `run_bot.bat --live` |
| `stop_bot.bat` | `STOP` file bana deta hai — **kill switch ON**, bot 1 second me band |
| `resume_bot.bat` | `STOP` file hata deta hai — kill switch OFF |

`run_bot.bat` khud ye handle karta hai:

| Exit code | Kya hua | Restart? |
|---|---|---|
| `0` | Bot normal band (jaise STOP file) | nahi |
| `2` | Galat command / flag, ya venv nahi mila | nahi |
| `3` | **Token expire (`invalid_grant`)** — message dikhega, koi restart nahi | nahi |
| `1` | Koi aur error | haan — 60 sec gap ke saath, max 20 baar |

Restart settings env se badal sakte ho (optional):

```
set BOT_MAX_RESTARTS=50
set BOT_RESTART_DELAY=120
```

---

## 3. Kill switch (turant band karna)

```bat
stop_bot.bat          :: STOP file banta hai - bot band, koi post nahi
resume_bot.bat        :: STOP file hata deta hai - bot dobara chalega
```

Ya manually: `del STOP`

Bot loop ke andar har ~1 second me `STOP` file check hota hai, isliye band karna
foran hota hai — pending post bhi nahi hote.

---

## 4. Autostart (login ke baad khud chal jaaye)

### Option A — Startup folder (simple, recommended, bina admin permission)

Shortcut ka target `D:\yt-bot\run_bot.bat` aur Start-in `D:\yt-bot` rakho, window **minimized** (7) chalega taaki login pe kala cmd window na uche.

PowerShell se (ek baar, admin permission nahi chahiye):

```powershell
$startup = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startup 'YT Comment Bot.lnk'
if (-not (Test-Path $shortcutPath)) {
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($shortcutPath)
    $s.TargetPath = 'D:\yt-bot\run_bot.bat'
    $s.WorkingDirectory = 'D:\yt-bot'
    $s.WindowStyle = 7          :: 7 = minimized
    $s.Description = 'YouTube Comment Bot - autostart on login'
    $s.Save()
}
```

Ya manually: `Win + R` → `shell:startup` → Enter → `run_bot.bat` ka shortcut banao → Right-click → Properties → Shortcut tab → "Run:" me **Minimized** chuno → "Start in:" me `D:\yt-bot` daalo.

Ab har login ke baad bot apne aap chalega (`MODE=draft` default → koi YouTube post nahi).

Chalane se pehle ek baar `run_bot.bat` double-click karke dekh lo ki sahi chalta hai.

#### Shortcut hatana (autostart band karna)

Startup folder (`shell:startup`) se `YT Comment Bot.lnk` delete kar do. Bot phir login pe apne aap nahi chalega; manually `run_bot.bat` se chala sakte ho.

### Option B — Task Scheduler (thoda advance, band kar bhi sakte ho)

1. `Win + R` → `taskschd.msc` → Enter
2. Right side me **Create Task** (not "Create Basic Task")
3. **General tab**: Name = `YT Comment Bot`, "Run whether user is logged on or not" chuno
   (password puchega) ya "Run only when user is logged on" chuno — dono chalega
4. **Triggers tab** → New → `At log on` → OK
5. **Actions tab** → New →
   - Action: `Start a program`
   - Program/script: `D:\yt-bot\run_bot.bat` (tumhara asli path)
   - Start in: `D:\yt-bot`
6. **Conditions tab**: "Start the task only if the computer is on AC power" **hata do**
   (warna laptop pe battery par start na ho)
7. **Settings tab**: "If the task fails, restart every 1 minute" chho sakte ho —
   `run_bot.bat` khud handle karta hai
8. OK → Task Scheduler me task **Right-click → Run** karke test karo

> Bot me pehle se hi double-run protection hai (`bot.lock` file) — agar galti se
> task dobara start ho jaye to dusra instance turant bahar nikal jaata hai.

---

## 5. Log aur files (ye sab `.gitignore` me hain)

| File | Kya hai |
|---|---|
| `bot.log` | Saari activity (comment ka 100 char tak, API keys kabhi nahi) |
| `bot.db` | SQLite database — replies, drafts, quota counter, video cache |
| `bot.lock` | Ek instance ka lock (30 min stale hone par apne aap free) |
| `STOP` | Kill switch marker file — iska matlab "band" |
| `token.json` | OAuth token (expire ho to delete + dobara login) |

Draft review:

```
venv\Scripts\python.exe review.py --drafts     :: draft replies poora text
venv\Scripts\python.exe review.py --today      :: aaj ki saari rows
venv\Scripts\python.exe review.py --stats      :: total + status/reason counts
```

---

## 6. Troubleshooting

| Dikha | Kaam |
|---|---|
| `Token expire ho gaya...` (exit 3) | `token.json` delete karo, phir `python main.py --once` chalao aur browser me login karo. `run_bot.bat` is par restart nahi karta. |
| `Ek aur instance chal raha hai (bot.lock ...)` | Pehle wala instance abhi zinda hai. Yaad hai? `bot.lock` 30 min purana hoga tab stale maana jayega. |
| `STOP file mila` | Kill switch on hai — `resume_bot.bat` chalao. |
| `403 quotaExceeded` | Aaj ki YouTube quota khatam. Bot aaj ke liye ruk jaata hai, kal khud chalega. |
| `Quota aaj: 8000/8000 units` | Local limit (config `QUOTA_LIMIT`) — `.env`/config me set hai. |
| Bot chal raha hai par reply nahi | `.env` me `MODE` dekho — `draft` me reply sirf db me save hoti hai (`review.py --drafts` se dekh lo). |

---

## 7. Safety (yaad rakhne wali baatein)

- Default `MODE=draft` — **koi post nahi** hota jab tak tum `auto` + `--live` na karo.
- Har reply ke beech random delay hai — quota (10,000 units/day) aur spam rules ka khayal.
- Institute replies me phone/link sirf daily cap (10 contact / 15 link) tak jate hain.
- `invalid_grant` par bot khud restart nahi karta — pehle login fix karna padta hai.
