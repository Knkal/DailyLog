@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === DailyLog Desktop App Launcher (Auto-detect Python) ===
set "APPDIR=%~dp0"
pushd "%APPDIR%"

echo [Run] App directory: %CD%

REM 1) Prefer local venv
set "PYEXE="
if exist ".venv\Scripts\python.exe" (
    set "PYEXE=%CD%\.venv\Scripts\python.exe"
    echo [Run] Using local venv Python: "%PYEXE%"
)

REM 2) Windows 'py' launcher
if not defined PYEXE (
    for /f "usebackq delims=" %%I in (`py -0p 2^>nul`) do (
        set "PYEXE=%%I"
        echo [Run] Using Windows 'py' launcher Python: "%%I"
        goto :have_py
    )
)

REM 3) python.exe on PATH
if not defined PYEXE (
    where python.exe >nul 2>&1
    if not errorlevel 1 (
        for /f "usebackq delims=" %%I in (`where python.exe`) do (
            set "PYEXE=%%I"
            echo [Run] Using PATH Python: "%%I"
            goto :have_py
        )
    )
)

:have_py
if not defined PYEXE (
    echo [!] Python 3.10+ not found.
    echo     Install from https://www.python.org/downloads/windows/ or enable the 'py' launcher.
    pause
    popd
    exit /b 103
)

REM Ensure venv
if not exist ".venv\Scripts\activate.bat" (
    echo [Run] Creating virtual environment...
    "%PYEXE%" -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create venv.
        pause
        popd
        exit /b 104
    )
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [!] Failed to activate venv.
    pause
    popd
    exit /b 105
)

echo [Run] Ensuring pip is up-to-date...
python -m pip install --upgrade pip >nul

if exist "requirements.txt" (
    echo [Run] Installing requirements...
    pip install -r requirements.txt
)

echo [Run] Starting app with venv Python...
python main.py
set "ERR=%ERRORLEVEL%"

echo [Run] App exited with code %ERR%
call ".venv\Scripts\deactivate.bat" 2>nul & rem ignore deactivate errors
popd

REM Optional: uncomment to debug window close
REM pause

exit /b %ERR%
