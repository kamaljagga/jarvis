@echo off
echo ================================================
echo  J.A.R.V.I.S — Virtual Environment Setup
echo  Python 3.12 recommended (3.13 has some issues
echo  with pyaudio and vosk on Windows)
echo ================================================

REM ── Check Python version ──────────────────────────
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install from python.org
    pause & exit
)

REM ── Create venv ───────────────────────────────────
echo.
echo [1/5] Creating virtual environment...
python -m venv venv_jarvis

REM ── Activate ──────────────────────────────────────
echo [2/5] Activating venv...
call venv_jarvis\Scripts\activate.bat

REM ── Upgrade pip ───────────────────────────────────
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip

REM ── Install PC dependencies ───────────────────────
echo [4/5] Installing packages...
pip install ^
    SpeechRecognition ^
    pyttsx3 ^
    gTTS ^
    playsound==1.2.2 ^
    sounddevice ^
    numpy ^
    pyautogui ^
    pywhatkit ^
    requests ^
    psutil ^
    pyperclip ^
    vosk ^
    pycaw ^
    comtypes

REM ── Done ──────────────────────────────────────────
echo [5/5] Done!
echo.
echo ================================================
echo  To activate venv next time:
echo    venv_jarvis\Scripts\activate.bat
echo  To run Jarvis:
echo    python pc\main_ai.py
echo ================================================
pause
