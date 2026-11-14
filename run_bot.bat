@echo off
REM ===================================================================
REM run_bot.bat - YouTube comment bot ka Windows runner (loop mode)
REM
REM   run_bot.bat            -> main.py --loop   (MODE .env se: draft = koi post nahi)
REM   run_bot.bat --live     -> main.py --loop --live (MODE=auto ho tabhi asli post)
REM
REM Exit code 3 (token expire / invalid_grant) par RESTART NAHI hota -
REM pehle dobara login karna hota hai.
REM
REM Test hook: BOT_TEST_EXIT env var se python chala ke exit code
REM simulate kiya ja sakta hai (sirf test_runner.py ke liye).
REM ===================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ===== Restart settings (env se override kar sakte ho) =====
set "MAX_RESTARTS=20"
set "RESTART_DELAY=60"
if defined BOT_MAX_RESTARTS set "MAX_RESTARTS=%BOT_MAX_RESTARTS%"
if defined BOT_RESTART_DELAY set "RESTART_DELAY=%BOT_RESTART_DELAY%"

set /a tries=0

REM ===== Test hook: python chala ke exit code jaisa behave karo =====
if defined BOT_TEST_EXIT goto run

REM ===== 1) Kill switch: STOP file ho to shuru hi mat karo =====
if exist "%~dp0STOP" (
    echo [run_bot] STOP file mila - bot nahi chala. Resume ke liye: del STOP
    exit /b 0
)

REM ===== 2) Python (venv) milega? =====
set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [run_bot] venv\Scripts\python.exe nahi mila - pehle venv banao.
    exit /b 2
)

:run
if defined BOT_TEST_EXIT (
    set "CODE=%BOT_TEST_EXIT%"
) else (
    "%PY%" main.py --loop %*
    set "CODE=!ERRORLEVEL!"
)

echo [run_bot] Bot exit code: !CODE!

REM ===== Exit 0 = normal band (jaise STOP file) - restart nahi =====
if "!CODE!"=="0" goto done

REM ===== Exit 2 = galat flag/command - restart nahi (loop phir se fail hoga) =====
if "!CODE!"=="2" (
    echo [run_bot] Exit 2 = galat command ya flag - restart nahi karunga.
    goto done
)

REM ===== Exit 3 = token expire (invalid_grant) - sirf message, NO restart =====
if "!CODE!"=="3" (
    echo [run_bot] Token expire ho gaya. token.json delete karke python main.py --once chalao aur dobara login karo.
    echo [run_bot] Restart nahi karunga - pehle login fix karo.
    goto done
)

REM ===== Baaki error: thoda ruk kar dobara chalao =====
set /a tries+=1
if !tries! gtr !MAX_RESTARTS! (
    echo [run_bot] !MAX_RESTARTS! baar restart ho gaya - ab ruk raha hoon.
    goto done
)
echo [run_bot] Bot band hua - !RESTART_DELAY! sec baad dobara chalaunga.
ping -n !RESTART_DELAY! 127.0.0.1 >nul
goto run

:done
exit /b !CODE!
