@echo off
chcp 65001 >nul
title Fix DeepSeek DNS - Hello-Agents

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [!] Requires Administrator privileges.
    echo.
    echo   Close this window, then RIGHT-CLICK this file
    echo   and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

set "HOSTS=%SystemRoot%\System32\drivers\etc\hosts"
set "BAK=%HOSTS%.ha-backup-20260915"
set "IP=183.131.191.171"
set "DOMAIN=api.deepseek.com"

echo.
echo   Target : %HOSTS%
echo   Entry  : %IP%  %DOMAIN%
echo.

if not exist "%BAK%" (
    copy /Y "%HOSTS%" "%BAK%" >nul
    if errorlevel 1 (
        echo   [X] Backup failed. Aborting, nothing was changed.
        pause
        exit /b 1
    )
    echo   [OK] Backup created: %BAK%
) else (
    echo   [i] Backup already exists, keeping it: %BAK%
)

findstr /I /C:"%DOMAIN%" "%HOSTS%" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [i] An entry for %DOMAIN% already exists - nothing added.
) else (
    >>"%HOSTS%" echo.
    >>"%HOSTS%" echo # Hello-Agents: bypass poisoned internal DNS (added 2026-09-15)
    >>"%HOSTS%" echo %IP% %DOMAIN%
    if errorlevel 1 (
        echo   [X] Failed to write hosts file.
        pause
        exit /b 1
    )
    echo   [OK] Entry added.
)

ipconfig /flushdns >nul
echo   [OK] DNS cache flushed.

echo.
echo   ---- current entries for %DOMAIN% ----
type "%HOSTS%" | findstr /I /C:"%DOMAIN%"
echo   --------------------------------------
echo.
echo   Rollback: delete the lines above, or restore from
echo   %BAK%
echo.
pause
