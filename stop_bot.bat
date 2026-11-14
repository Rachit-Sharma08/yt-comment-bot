@echo off
REM ===================================================================
REM stop_bot.bat - kill switch ON (bot band)
REM
REM Is folder me "STOP" file ban jaata hai - bot ka loop 1 second me
REM me band ho jaata hai aur koi bhi reply post nahi hoti.
REM Resume:  del STOP   (ya resume_bot.bat)
REM ===================================================================
cd /d "%~dp0"

if exist "%~dp0STOP" (
    echo [stop_bot] STOP file pehle se hai - bot pehle se band hai.
) else (
    type nul > "%~dp0STOP"
    echo [stop_bot] STOP file bana diya - bot band ho jayega.
)
