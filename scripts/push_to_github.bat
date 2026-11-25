@echo off
setlocal
cd /d "%~dp0"
title Push Calling Agent Platform to GitHub

echo =======================================================================
echo          ARB SoftTech Calling Agent - Push to GitHub
echo =======================================================================
echo.
echo Target Repository: https://github.com/Omdaware05/Calling-Agent-SAAS-.git
echo Branch:            main
echo.
echo Executing git push...
echo (If a GitHub login prompt appears, sign in with your GitHub account)
echo.

git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Push failed or was canceled.
    echo If authentication failed, ensure you are logged into GitHub as 'Omdaware05'.
) else (
    echo.
    echo =======================================================================
    echo [SUCCESS] Successfully uploaded to:
    echo https://github.com/Omdaware05/Calling-Agent-SAAS-
    echo =======================================================================
)

echo.
pause
