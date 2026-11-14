@echo off
REM ===================================================================
REM resume_bot.bat - kill switch OFF (STOP file hata do)
REM Sirf tab chalao jab tumhe sach me bot dobara chalana ho.
REM ===================================================================
cd /d "%~dp0"

if exist "%~dp0STOP" (
    del "%~dp0STOP"
    echo [resume_bot] STOP file hata diya - bot ab chal sakta hai.
) else (
    echo [resume_bot] STOP file nahi tha - kuch nahi kiya.
)
