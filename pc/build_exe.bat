@echo off
echo ================================================
echo  J.A.R.V.I.S — Build EXE
echo ================================================

REM ── Activate venv if it exists ────────────────────
if exist "..\venv_jarvis\Scripts\activate.bat" (
    call ..\venv_jarvis\Scripts\activate.bat
    echo [OK] venv activated
) else (
    echo [WARN] No venv found, using system Python
)

REM ── Install PyInstaller if missing ────────────────
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [1/4] Installing PyInstaller...
    pip install pyinstaller
) else (
    echo [1/4] PyInstaller already installed
)

REM ── Install UPX for smaller EXE (optional) ────────
where upx >nul 2>&1
if errorlevel 1 (
    echo [2/4] UPX not found - EXE will be slightly larger (that is okay)
) else (
    echo [2/4] UPX found - EXE will be compressed
)

REM ── Clean old build ───────────────────────────────
echo [3/4] Cleaning old build...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist Jarvis.exe del Jarvis.exe

REM ── Build EXE ─────────────────────────────────────
echo [4/4] Building EXE — this takes 2-5 minutes...
echo.
pyinstaller jarvis.spec

REM ── Check result ──────────────────────────────────
if exist "dist\Jarvis.exe" (
    echo.
    echo ================================================
    echo  SUCCESS! EXE built at:
    echo  dist\Jarvis.exe
    echo.
    echo  Copy these to the same folder as Jarvis.exe:
    echo    contacts.json
    echo    settings.json
    echo    model\  (Vosk model folder)
    echo ================================================

    REM Copy EXE to project root for convenience
    copy "dist\Jarvis.exe" "..\Jarvis.exe" >nul
    echo  Also copied to project root as Jarvis.exe
) else (
    echo.
    echo [ERROR] Build failed! Check the errors above.
    echo Common fixes:
    echo   - pip install pyinstaller --upgrade
    echo   - Make sure all imports in main_ai.py are installed
)

pause
