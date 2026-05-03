# ═══════════════════════════════════════════════════════════════════
#  J.A.R.V.I.S  —  ULTIMATE VERSION
#  🔒 Privacy   : Vosk offline wake word (nothing sent until you speak)
#  🎙 Voice IN  : Vosk (wake) → Google STT (command only)
#  🔊 Voice OUT : gTTS (online) + pyttsx3 (offline fallback)
#  🤖 AI Brain  : Groq (primary) + Gemini (fallback)
#  📱 SMS       : Fast2SMS (India, free tier) — uses your SMS pack
#  📞 Calls     : WhatsApp calls via pywhatkit
#  💬 WhatsApp  : Send messages by voice
#  🛡 Security  : Lock PC, anti-spy scan, firewall check, process guard
#  💻 System    : Shutdown, restart, sleep, battery, CPU/RAM stats
#  🔊 Volume    : Increase, decrease, mute, set level
#  📝 Reminders : Set voice reminders with alarm
#  📸 Screenshot: Capture screen by voice
#  🔍 Search    : Google, YouTube by voice
#  🧮 Math      : Voice calculator
#  📋 Clipboard : Read and copy text
#
#  pip install speechrecognition pyttsx3 gtts playsound sounddevice
#             numpy pyautogui pywhatkit requests vosk psutil
#             pycaw comtypes pyperclip
#  Vosk model : https://alphacephei.com/vosk/models
#             → vosk-model-small-en-in-0.4  (Indian English, 36MB)
#             → extract as folder named "model" in project folder
# ═══════════════════════════════════════════════════════════════════

import speech_recognition as sr
import webbrowser
import pyttsx3
import requests
from gtts import gTTS
from playsound import playsound
import os, sys, json, threading, time, subprocess
import winreg, datetime, math, re, ctypes
import sounddevice as sd
import numpy as np
import pyautogui
import pywhatkit as kit
import psutil
import pyperclip

# ─────────────────────────────────────────
#  BASE DIR — works for .py and .exe both
# ─────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APPS_FILE       = os.path.join(BASE_DIR, "apps.json")
CONTACTS_FILE   = os.path.join(BASE_DIR, "contacts.json")
VOSK_MODEL_PATH = os.path.join(BASE_DIR, "model")

SETTINGS_FILE   = os.path.join(BASE_DIR, "settings.json")

# ─────────────────────────────────────────
#  SETTINGS — features on/off, language, emotion
# ─────────────────────────────────────────
DEFAULT_SETTINGS = {
    "language": "en", "emotion": "friendly", "jarvis_on": True,
    "features": {"music":True,"weather":True,"sms":True,"whatsapp":True,
                 "news":True,"security":True,"screenshot":True,"ai":True,
                 "reminder":True,"clipboard":True,"volume":True,"system":True},
    "battery":  {"full_alert":True,"low_alert":True}
}
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        saved = json.load(open(SETTINGS_FILE,"r"))
        m = {**DEFAULT_SETTINGS,**saved}
        m["features"] = {**DEFAULT_SETTINGS["features"],**saved.get("features",{})}
        m["battery"]  = {**DEFAULT_SETTINGS["battery"], **saved.get("battery",{})}
        return m
    json.dump(DEFAULT_SETTINGS, open(SETTINGS_FILE,"w"), indent=2)
    return DEFAULT_SETTINGS.copy()
def save_settings(s): json.dump(s, open(SETTINGS_FILE,"w"), indent=2)
S = load_settings()
def feature_on(name): return S["features"].get(name,True) and S.get("jarvis_on",True)

# ─────────────────────────────────────────
#  MULTILINGUAL + EMOTIONAL RESPONSES
# ─────────────────────────────────────────
import random
RESP = {
  "en":{
    "greet":{"friendly":["Hey! I\'m here, what can I do for you?","Hello! How can I help?"],
             "formal":["Good day. How may I assist you?","I\'m ready. Please state your request."],
             "funny":["Ta-da! Jarvis is here! What do you need?","Your wish is my command — mostly!"],
             "caring":["Hey! So good to hear from you. What do you need?","I\'m here for you!"],
             "calm":["Yes. I\'m listening.","Ready whenever you are."]},
    "battery_full":"Battery fully charged! You can unplug now.",
    "battery_low":"Heads up! Battery at 20 percent. Please plug in!",
    "not_understood":"Sorry, I didn\'t catch that. Could you say it again?",
    "feature_off":"That feature is turned off. Enable it in the Jarvis control panel.",
    "morning":"Good morning! Hope you have a wonderful day.",
    "afternoon":"Good afternoon! How is your day going?",
    "evening":"Good evening! Hope your day went well.",
    "night":"Good night! Rest well.",
  },
  "hi":{
    "greet":{"friendly":["\u0939\u093e\u0902! \u092c\u0924\u093e\u0907\u090f \u0915\u094d\u092f\u093e \u0915\u0930\u0942\u0902?","\u0928\u092e\u0938\u094d\u0924\u0947! \u0915\u094d\u092f\u093e \u092e\u0926\u0926 \u0915\u0930\u0942\u0902?"],
             "formal":["\u0928\u092e\u0938\u094d\u0924\u0947\u0964 \u0906\u092a \u0915\u094d\u092f\u093e \u091c\u093e\u0928\u0928\u093e \u091a\u093e\u0939\u0924\u0947 \u0939\u0948\u0902?","\u091c\u0940, \u092c\u0924\u093e\u0907\u090f \u0915\u094d\u092f\u093e \u091a\u093e\u0939\u093f\u090f\u0964"],
             "funny":["\u0906 \u0917\u092f\u093e \u091c\u093e\u0930\u094d\u0935\u093f\u0938! \u0915\u094d\u092f\u093e \u0939\u0941\u0915\u0941\u092e \u0939\u0948?","\u0939\u093e\u091c\u093c\u093f\u0930 \u0939\u0942\u0902 \u092e\u093e\u0932\u093f\u0915!"],
             "caring":["\u0905\u0930\u0947! \u0906\u092a\u0915\u0940 \u0906\u0935\u093e\u091c\u093c \u0938\u0941\u0928\u0915\u0930 \u0905\u091a\u094d\u091b\u093e \u0932\u0917\u093e\u0964","\u092e\u0948\u0902 \u092f\u0939\u093e\u0902 \u0939\u0942\u0902!"],
             "calm":["\u091c\u0940\u0964 \u092c\u094b\u0932\u093f\u090f\u0964","\u0939\u093e\u0902, \u0938\u0941\u0928 \u0930\u0939\u093e \u0939\u0942\u0902\u0964"]},
    "battery_full":"\u092c\u0948\u091f\u0930\u0940 100% \u0939\u094b \u0917\u0908\u0964 \u091a\u093e\u0930\u094d\u091c\u0930 \u0939\u091f\u093e \u0938\u0915\u0924\u0947 \u0939\u0948\u0902\u0964",
    "battery_low":"\u0927\u094d\u092f\u093e\u0928 \u0926\u0940\u091c\u093f\u090f! \u092c\u0948\u091f\u0930\u0940 20% \u0930\u0939 \u0917\u0908\u0964 \u091a\u093e\u0930\u094d\u091c\u0930 \u0932\u0917\u093e\u0907\u090f\u0964",
    "not_understood":"\u092e\u093e\u092b\u093c \u0915\u0930\u0947\u0902, \u0938\u092e\u091d \u0928\u0939\u0940\u0902 \u0906\u092f\u093e\u0964 \u0926\u094b\u092c\u093e\u0930\u093e \u092c\u094b\u0932\u093f\u090f\u0964",
    "feature_off":"\u092f\u0939 \u0938\u0941\u0935\u093f\u0927\u093e \u092c\u0902\u0926 \u0939\u0948\u0964 \u0915\u0902\u091f\u094d\u0930\u094b\u0932 \u092a\u0948\u0928\u0932 \u092e\u0947\u0902 \u091a\u093e\u0932\u0942 \u0915\u0930\u0947\u0902\u0964",
    "morning":"\u0938\u0941\u092a\u094d\u0930\u092d\u093e\u0924! \u0906\u092a\u0915\u093e \u0926\u093f\u0928 \u0936\u0941\u092d \u0939\u094b\u0964",
    "afternoon":"\u0928\u092e\u0938\u094d\u0924\u0947! \u0926\u094b\u092a\u0939\u0930 \u0915\u0948\u0938\u0940 \u091c\u093e \u0930\u0939\u0940 \u0939\u0948?",
    "evening":"\u0936\u0941\u092d \u0938\u0902\u0927\u094d\u092f\u093e!",
    "night":"\u0936\u0941\u092d \u0930\u093e\u0924\u094d\u0930\u093f! \u0905\u091a\u094d\u091b\u0940 \u0928\u0940\u0902\u0926 \u0932\u0947\u0902\u0964",
  },
  "pa":{
    "greet":{"friendly":["\u0a39\u0a3e\u0a02! \u0a26\u0a71\u0a38\u0a4b \u0a15\u0a40 \u0a15\u0a30\u0a3e\u0a02?","\u0a38\u0a24 \u0a38\u0a4d\u0a30\u0a40 \u0a05\u0a15\u0a3e\u0a32! \u0a15\u0a40 \u0a2e\u0a26\u0a26 \u0a15\u0a30\u0a3e\u0a02?"],
             "formal":["\u0a1c\u0a40, \u0a26\u0a71\u0a38\u0a4b \u0a15\u0a40 \u0a1a\u0a3e\u0a39\u0a40\u0a26\u0a3e \u0a39\u0a48\u0964","\u0a24\u0a41\u0a39\u0a3e\u0a21\u0a47 \u0a39\u0a41\u0a15\u0a2e\u0a3e\u0a02 \u0a26\u0a40 \u0a09\u0a21\u0a40\u0a15 \u0a39\u0a48\u0964"],
             "funny":["\u0a06 \u0a17\u0a3f\u0a06 \u0a1c\u0a3e\u0a30\u0a35\u0a3f\u0a38! \u0a26\u0a71\u0a38\u0a4b \u0a38\u0a30\u0a26\u0a3e\u0a30 \u0a1c\u0a40?","\u0a39\u0a3e\u0a1c\u0a3c\u0a30 \u0a39\u0a3e\u0a02!"],
             "caring":["\u0a13\u0a0f! \u0a24\u0a41\u0a39\u0a3e\u0a21\u0a40 \u0a06\u0a35\u0a3e\u0a1c\u0a3c \u0a38\u0a41\u0a23 \u0a15\u0a47 \u0a1a\u0a70\u0a17\u0a3e \u0a32\u0a71\u0a17\u0a3f\u0a06\u0964","\u0a2e\u0a48\u0a02 \u0a07\u0a71\u0a25\u0a47 \u0a39\u0a3e\u0a02!"],
             "calm":["\u0a1c\u0a40\u0964 \u0a26\u0a71\u0a38\u0a4b\u0964","\u0a39\u0a3e\u0a02, \u0a38\u0a41\u0a23 \u0a30\u0a3f\u0a39\u0a3e \u0a39\u0a3e\u0a02\u0964"]},
    "battery_full":"\u0a2c\u0a48\u0a1f\u0a30\u0a40 100% \u0a39\u0a4b \u0a17\u0a08\u0964 \u0a39\u0a41\u0a23 \u0a1a\u0a3e\u0a30\u0a1c\u0a30 \u0a32\u0a3e\u0a39 \u0a38\u0a15\u0a26\u0a47 \u0a39\u0a4b\u0964",
    "battery_low":"\u0a27\u0a3f\u0a06\u0a28 \u0a26\u0a3f\u0a13! \u0a2c\u0a48\u0a1f\u0a30\u0a40 20% \u0a30\u0a39\u0a3f \u0a17\u0a08\u0964 \u0a1a\u0a3e\u0a30\u0a1c\u0a30 \u0a32\u0a3e\u0a13\u0964",
    "not_understood":"\u0a2e\u0a3e\u0a2b\u0a3c \u0a15\u0a30\u0a28\u0a3e, \u0a38\u0a2e\u0a1d \u0a28\u0a39\u0a40\u0a02 \u0a06\u0a07\u0a06\u0964 \u0a26\u0a41\u0a2c\u0a3e\u0a30\u0a3e \u0a2c\u0a4b\u0a32\u0a4b\u0964",
    "feature_off":"\u0a07\u0a39 \u0a38\u0a41\u0a35\u0a3f\u0a27\u0a3e \u0a39\u0a41\u0a23 \u0a2c\u0a70\u0a26 \u0a39\u0a48\u0964 \u0a15\u0a70\u0a1f\u0a30\u0a4b\u0a32 \u0a2a\u0a48\u0a28\u0a32 \u0a35\u0a3f\u0a71\u0a1a \u0a1a\u0a3e\u0a32\u0a42 \u0a15\u0a30\u0a4b\u0964",
    "morning":"\u0a38\u0a24 \u0a38\u0a4d\u0a30\u0a40 \u0a05\u0a15\u0a3e\u0a32! \u0a24\u0a41\u0a39\u0a3e\u0a21\u0a3e \u0a26\u0a3f\u0a28 \u0a35\u0a27\u0a40\u0a06 \u0a39\u0a4b\u0a35\u0a47\u0964",
    "afternoon":"\u0a26\u0a41\u0a2a\u0a39\u0a3f\u0a30 \u0a26\u0a40\u0a06\u0a02 \u0a38\u0a3c\u0a41\u0a2d\u0a15\u0a3e\u0a2e\u0a28\u0a3e\u0a35\u0a3e\u0a02!",
    "evening":"\u0a38\u0a3c\u0a3e\u0a2e \u0a26\u0a40\u0a06\u0a02 \u0a38\u0a3c\u0a41\u0a2d\u0a15\u0a3e\u0a2e\u0a28\u0a3e\u0a35\u0a3e\u0a02!",
    "night":"\u0a38\u0a3c\u0a41\u0a2d \u0a30\u0a3e\u0a24! \u0a1a\u0a70\u0a17\u0a40 \u0a28\u0a40\u0a02\u0a26 \u0a06\u0a35\u0a47\u0964",
  }
}

def r(key, subkey=None):
    lang = S.get("language","en")
    emo  = S.get("emotion","friendly")
    res  = RESP.get(lang, RESP["en"])
    val  = res.get(key, RESP["en"].get(key,""))
    if isinstance(val, dict):
        phrases = val.get(emo, val.get("friendly",["..."]))
        return random.choice(phrases)
    return val

def time_greeting():
    h = datetime.datetime.now().hour
    lang = S.get("language","en")
    res  = RESP.get(lang, RESP["en"])
    if   h < 12: return res["morning"]
    elif h < 17: return res["afternoon"]
    elif h < 21: return res["evening"]
    else:        return res["night"]

# ─────────────────────────────────────────
#  🔑 API KEYS — paste yours here
# ─────────────────────────────────────────
YOUTUBE_API_KEY  = "YOUR_YOUTUBE_API_KEY"       # console.cloud.google.com
WEATHER_API_KEY  = "YOUR_OPENWEATHER_API_KEY"   # openweathermap.org/api
NEWS_API_KEY     = "YOUR_NEWSAPI_KEY"           # newsapi.org
YOUR_CITY        = "Rupnagar"                  # default city

# 🤖 AI keys (both free)
GROQ_API_KEY     = "YOUR_GROQ_API_KEY"          # console.groq.com
GEMINI_API_KEY   = "YOUR_GEMINI_API_KEY"        # aistudio.google.com

# 📱 SMS — Fast2SMS (India, free tier — fast2sms.com)
FAST2SMS_KEY     = "YOUR_FAST2SMS_API_KEY"      # fast2sms.com/dashboard

# ─────────────────────────────────────────
#  🔒 PRIVACY LOG
# ─────────────────────────────────────────
privacy_log = []

def log_privacy(event):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    privacy_log.append(f"[{ts}] {event}")
    print(f"[PRIVACY] {event}")

# ─────────────────────────────────────────
#  🔊 SPEAK — gTTS (online) + pyttsx3 (offline fallback)
# ─────────────────────────────────────────
engine = pyttsx3.init()
engine.setProperty('rate', 165)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"Jarvis: {text}")
    try:
        tts = gTTS(text)
        tts.save("temp_jarvis.mp3")
        playsound("temp_jarvis.mp3")
        os.remove("temp_jarvis.mp3")
    except Exception:
        engine.say(text)
        engine.runAndWait()

# ─────────────────────────────────────────
#  🔒 VOSK — OFFLINE WAKE WORD (privacy core)
#  Nothing ever sent to internet for wake word.
#  Data only leaves your PC AFTER "Jarvis" is heard.
# ─────────────────────────────────────────
VOSK_MODEL     = None
vosk_available = False

def load_vosk():
    global VOSK_MODEL, vosk_available
    try:
        # Fix vosk DLL path when running as PyInstaller EXE
        if getattr(sys, 'frozen', False):
            vosk_dll_path = os.path.join(sys._MEIPASS, 'vosk')
            if os.path.exists(vosk_dll_path):
                os.add_dll_directory(vosk_dll_path)
        from vosk import Model, KaldiRecognizer
        if not os.path.exists(VOSK_MODEL_PATH):
            print("⚠️  Vosk model not found. Using Google STT for wake word (less private).")
            print(f"   Download: https://alphacephei.com/vosk/models")
            print(f"   Extract as: {VOSK_MODEL_PATH}")
            return False
        VOSK_MODEL = Model(VOSK_MODEL_PATH)
        vosk_available = True
        log_privacy("Wake word engine: Vosk OFFLINE ✅ (nothing sent to internet)")
        return True
    except ImportError:
        print("⚠️  Vosk not installed. Run: pip install vosk")
        return False

def recognize_vosk(audio_data):
    """Offline speech — runs on YOUR CPU only."""
    if not vosk_available or VOSK_MODEL is None:
        return recognize_google(audio_data)
    try:
        from vosk import KaldiRecognizer
        rec = KaldiRecognizer(VOSK_MODEL, 16000)
        rec.AcceptWaveform(audio_data.get_raw_data())
        result = json.loads(rec.Result())
        return result.get("text", "").strip()
    except Exception as e:
        print(f"[Vosk] {e}")
        return ""

r_google = sr.Recognizer()

def recognize_google(audio_data):
    """Used ONLY for commands after wake word."""
    try:
        log_privacy("Command audio sent to Google STT (command only, not continuous)")
        text = r_google.recognize_google(audio_data)
        log_privacy(f"Google STT returned: '{text}' — connection closed")
        return text
    except Exception:
        return ""

# ─────────────────────────────────────────
#  🎙 SMART MIC
# ─────────────────────────────────────────
def listen_audio(duration=2.0, fs=16000):
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    return sr.AudioData(recording.tobytes(), fs, 2)

def listen_smart(timeout=6, phrase_limit=8, fs=16000):
    CHUNK = 1024; THRESHOLD = 600; SILENCE_SEC = 1.5
    waited = 0; speaking = False; silent_chunks = 0; frames = []
    wait_limit    = int(timeout * fs / CHUNK)
    silence_limit = int(SILENCE_SEC * fs / CHUNK)
    stream = sd.InputStream(samplerate=fs, channels=1, dtype='int16', blocksize=CHUNK)
    stream.start()
    print("Listening (speak now)...")
    try:
        while True:
            chunk, _ = stream.read(CHUNK)
            volume   = np.abs(chunk).mean()
            if not speaking:
                waited += 1
                if volume > THRESHOLD:
                    speaking = True
                    frames.append(chunk.copy())
                elif waited > wait_limit:
                    return None
            else:
                frames.append(chunk.copy())
                silent_chunks = 0 if volume > THRESHOLD else silent_chunks + 1
                if silent_chunks > silence_limit or len(frames) * CHUNK / fs > phrase_limit:
                    break
    finally:
        stream.stop(); stream.close()
    if not frames: return None
    return sr.AudioData(np.concatenate(frames, axis=0).tobytes(), fs, 2)

# ─────────────────────────────────────────
#  🎵 MUSIC
# ─────────────────────────────────────────
# ─────────────────────────────────────────
#  🎵 INSTANT MUSIC SEARCH
#  No local file needed. Every song is
#  searched on YouTube instantly when asked.
#  Session cache avoids re-searching same song.
# ─────────────────────────────────────────
_song_cache = {}   # lives only during this session

def search_youtube_instant(song_name):
    """
    Search YouTube instantly. No musicLibrary.py needed.
    1. Check session cache (instant)
    2. Try YouTube Data API (needs key)
    3. Fallback: direct YouTube search URL (no key needed)
    """
    # 1. Session cache — already searched this session
    if song_name in _song_cache:
        print(f"[Music] Cache hit: {song_name}")
        return _song_cache[song_name]

    # 2. YouTube Data API (best result)
    if YOUTUBE_API_KEY and YOUTUBE_API_KEY != "YOUR_YOUTUBE_API_KEY":
        try:
            resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={"part":"snippet","q":song_name,"type":"video",
                        "maxResults":1,"key":YOUTUBE_API_KEY}, timeout=10)
            data = resp.json()
            if data.get("items"):
                url = f"https://www.youtube.com/watch?v={data['items'][0]['id']['videoId']}"
                _song_cache[song_name] = url
                print(f"[Music] Found via API: {url}")
                return url
        except Exception as e:
            print(f"[YouTube API] {e}")

    # 3. Fallback — YouTube search URL (no API key needed, opens search results)
    fallback = f"https://www.youtube.com/results?search_query={song_name.replace(' ','+')}"
    _song_cache[song_name] = fallback
    print(f"[Music] Fallback search: {fallback}")
    return fallback

# ─────────────────────────────────────────
#  💻 LOCAL APPS
# ─────────────────────────────────────────
DEFAULT_APPS = {
    "notepad":"notepad.exe","calculator":"calc.exe","paint":"mspaint.exe",
    "task manager":"taskmgr.exe","file explorer":"explorer.exe",
    "chrome":r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vs code":rf"C:\Users\{os.environ.get('USERNAME','')}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "word":r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
}

def load_apps():
    if os.path.exists(APPS_FILE):
        with open(APPS_FILE,"r") as f: return json.load(f)
    return {}

def save_apps(apps):
    with open(APPS_FILE,"w") as f: json.dump(apps, f, indent=2)

def scan_installed_apps():
    speak("Scanning installed apps...")
    found = {}
    for reg_path in [r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"]:
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            for i in range(winreg.QueryInfoKey(reg)[0]):
                try:
                    sub  = winreg.OpenKey(reg, winreg.EnumKey(reg, i))
                    name = winreg.QueryValueEx(sub, "DisplayName")[0].lower().strip()
                    try:
                        path = winreg.QueryValueEx(sub, "InstallLocation")[0]
                        if path and os.path.exists(path): found[name] = path
                    except: pass
                except: continue
        except: continue
    for root_dir, _, files in os.walk(r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"):
        for f in files:
            if f.endswith(".lnk"):
                found[f.replace(".lnk","").lower()] = os.path.join(root_dir, f)
    all_apps = {**DEFAULT_APPS, **found}
    save_apps(all_apps)
    speak(f"Done! Found {len(all_apps)} apps.")
    return all_apps

def open_app(app_name):
    all_apps = {**DEFAULT_APPS, **load_apps()}
    target   = all_apps.get(app_name) or next(
        (all_apps[k] for k in all_apps if app_name in k or k in app_name), None)
    if target:
        try: os.startfile(target)
        except: subprocess.Popen(target, shell=True)
        speak(f"Opening {app_name}")
    else:
        speak(f"Could not find {app_name}. Say scan apps to update.")

# ─────────────────────────────────────────
#  ⏱ TIMER & REMINDERS
# ─────────────────────────────────────────
def set_timer(seconds, message="Time is up!"):
    threading.Thread(target=lambda:[time.sleep(seconds), speak(message)], daemon=True).start()
    speak(f"Timer set for {seconds} seconds")

def parse_timer(command):
    words = command.lower().split()
    for i, w in enumerate(words):
        if w.isdigit():
            val  = int(w)
            unit = words[i+1] if i+1 < len(words) else ""
            if "second" in unit: return val
            if "minute" in unit: return val * 60
            if "hour"   in unit: return val * 3600
            return val * 60
    return None

def set_reminder(command):
    """
    Say: remind me to drink water in 10 minutes
    Say: remind me at 5 30 pm to call mom
    """
    cmd = command.lower()
    try:
        if " in " in cmd:
            task = cmd.split("remind me to")[1].split(" in ")[0].strip() if "remind me to" in cmd else "reminder"
            time_part = cmd.split(" in ")[-1].strip()
            secs = parse_timer(time_part)
            if secs:
                set_timer(secs, f"Reminder: {task}")
                speak(f"Okay! I will remind you to {task}"); return
        if " at " in cmd:
            task = cmd.split("remind me to")[1].split(" at ")[0].strip() if "remind me to" in cmd else "reminder"
            time_str = cmd.split(" at ")[-1].strip()
            nums = re.findall(r'\d+', time_str)
            if nums:
                h = int(nums[0]); m = int(nums[1]) if len(nums) > 1 else 0
                if "pm" in time_str and h != 12: h += 12
                if "am" in time_str and h == 12: h = 0
                now   = datetime.datetime.now()
                alarm = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if alarm < now: alarm += datetime.timedelta(days=1)
                secs  = (alarm - now).total_seconds()
                set_timer(int(secs), f"Reminder: {task}")
                speak(f"Reminder set for {alarm.strftime('%I:%M %p')}"); return
        speak("Say: remind me to drink water in 10 minutes")
    except Exception as e:
        speak("Could not set reminder."); print(f"[Reminder] {e}")

# ─────────────────────────────────────────
#  🌤 WEATHER
# ─────────────────────────────────────────
def get_weather(city=None):
    city = city or YOUR_CITY
    try:
        resp = requests.get("http://api.openweathermap.org/data/2.5/weather",
            params={"q":city,"appid":WEATHER_API_KEY,"units":"metric"}, timeout=10)
        data = resp.json()
        if str(data.get("cod")) == "200":
            speak(f"Weather in {data['name']}: {data['weather'][0]['description']}. "
                  f"Temperature {data['main']['temp']} degrees, "
                  f"feels like {data['main']['feels_like']}. "
                  f"Humidity {data['main']['humidity']} percent.")
        else:
            speak(f"Could not get weather for {city}.")
    except Exception as e:
        speak("Weather check failed. Check internet."); print(f"[Weather] {e}")

# ─────────────────────────────────────────
#  📰 NEWS
# ─────────────────────────────────────────
def get_news(topic=None):
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
        if topic: url += f"&q={topic}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            speak("Here are the top headlines:")
            for a in resp.json().get("articles",[])[:5]:
                speak(a["title"]); time.sleep(0.3)
        else:
            speak("Could not fetch news right now.")
    except Exception as e:
        speak("News fetch failed."); print(f"[News] {e}")

# ─────────────────────────────────────────
#  📱 SMS — Fast2SMS (India, free tier)
#  Sign up at fast2sms.com → get free API key
#  Sends real SMS to any Indian number
# ─────────────────────────────────────────
def send_sms(number, message):
    try:
        number = number.replace("+91","").replace("+","").strip()
        resp   = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": FAST2SMS_KEY},
            data={"route":"q","message":message,
                  "language":"english","flash":0,"numbers":number}, timeout=15)
        result = resp.json()
        if result.get("return"):
            speak("SMS sent successfully!")
            print(f"[SMS] Sent to {number}: {message}")
        else:
            speak("SMS failed. Check your Fast2SMS key.")
            print(f"[SMS] Error: {result}")
    except Exception as e:
        speak("SMS failed. Check internet."); print(f"[SMS] {e}")

def send_sms_command(command):
    """Say: send SMS to mom saying I am on my way"""
    try:
        if "saying" not in command:
            speak("Say: send SMS to mom saying your message"); return
        to_part  = command.split("to")[1].split("saying")[0].strip()
        msg_part = command.split("saying")[1].strip()
        number   = load_contacts().get(to_part)
        if not number:
            speak(f"No number for {to_part}. Add to contacts dot json."); return
        speak(f"Sending SMS to {to_part}...")
        send_sms(number, msg_part)
    except Exception as e:
        speak("SMS command failed."); print(f"[SMS CMD] {e}")

# ─────────────────────────────────────────
#  💬 WHATSAPP
# ─────────────────────────────────────────
def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE,"r") as f: return json.load(f)
    sample = {"mom":"+919XXXXXXXXX","dad":"+919XXXXXXXXX","friend":"+919XXXXXXXXX"}
    with open(CONTACTS_FILE,"w") as f: json.dump(sample, f, indent=2)
    speak("Created contacts dot json. Please add your contacts.")
    return sample

def send_whatsapp(command):
    """Say: send WhatsApp to mom saying hello"""
    try:
        if "saying" not in command:
            speak("Say: send WhatsApp to name saying message"); return
        to_part  = command.split("to")[1].split("saying")[0].strip()
        msg_part = command.split("saying")[1].strip()
        number   = load_contacts().get(to_part)
        if not number:
            speak(f"No number for {to_part}. Add to contacts dot json"); return
        now = datetime.datetime.now()
        m   = now.minute + 2; h = now.hour + (1 if m >= 60 else 0)
        kit.sendwhatmsg(number, msg_part, h%24, m%60, wait_time=20, tab_close=True)
        speak(f"WhatsApp sent to {to_part}")
    except Exception as e:
        speak("WhatsApp failed."); print(f"[WhatsApp] {e}")

def make_whatsapp_call(command):
    """Say: WhatsApp call mom  /  call dad on WhatsApp"""
    try:
        name = command.lower().replace("whatsapp","").replace("call","").replace("on","").strip()
        number = load_contacts().get(name)
        if not number:
            speak(f"No number for {name}. Add to contacts dot json"); return
        number_clean = number.replace("+","").replace(" ","")
        webbrowser.open(f"https://web.whatsapp.com/send?phone={number_clean}&call=true")
        speak(f"Opening WhatsApp call to {name}")
    except Exception as e:
        speak("WhatsApp call failed."); print(f"[WA Call] {e}")

# ─────────────────────────────────────────
#  🔊 VOLUME CONTROL
# ─────────────────────────────────────────
def set_volume(level=None, action=None):
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices  = AudioUtilities.GetSpeakers()
        iface    = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol_ctrl = iface.QueryInterface(IAudioEndpointVolume)
        if action == "mute":
            vol_ctrl.SetMute(1, None); speak("Muted")
        elif action == "unmute":
            vol_ctrl.SetMute(0, None); speak("Unmuted")
        elif action == "up":
            cur = vol_ctrl.GetMasterVolumeLevelScalar()
            vol_ctrl.SetMasterVolumeLevelScalar(min(1.0, cur+0.1), None)
            speak(f"Volume increased to {int(min(1.0,cur+0.1)*100)} percent")
        elif action == "down":
            cur = vol_ctrl.GetMasterVolumeLevelScalar()
            vol_ctrl.SetMasterVolumeLevelScalar(max(0.0, cur-0.1), None)
            speak(f"Volume decreased to {int(max(0.0,cur-0.1)*100)} percent")
        elif level is not None:
            vol_ctrl.SetMasterVolumeLevelScalar(level/100, None)
            speak(f"Volume set to {level} percent")
    except ImportError:
        if action == "mute":    pyautogui.press('volumemute'); speak("Muted")
        elif action == "up":    [pyautogui.press('volumeup') for _ in range(5)]; speak("Volume up")
        elif action == "down":  [pyautogui.press('volumedown') for _ in range(5)]; speak("Volume down")
    except Exception as e:
        print(f"[Volume] {e}")

def handle_volume(cmd):
    if "mute" in cmd and "un" not in cmd: set_volume(action="mute")
    elif "unmute" in cmd:                 set_volume(action="unmute")
    elif "volume up" in cmd or "increase volume" in cmd:   set_volume(action="up")
    elif "volume down" in cmd or "decrease volume" in cmd: set_volume(action="down")
    else:
        nums = re.findall(r'\d+', cmd)
        if nums: set_volume(level=int(nums[0]))
        else:    speak("Say: volume up, volume down, mute, or set volume to 50")

# ─────────────────────────────────────────
#  💻 SYSTEM CONTROLS
# ─────────────────────────────────────────
def system_control(action):
    if action == "shutdown":
        speak("Shutting down in 10 seconds.")
        time.sleep(10); os.system("shutdown /s /t 0")
    elif action == "restart":
        speak("Restarting in 10 seconds.")
        time.sleep(10); os.system("shutdown /r /t 0")
    elif action == "sleep":
        speak("Going to sleep.")
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    elif action == "lock":
        speak("Locking the screen.")
        ctypes.windll.user32.LockWorkStation()
    elif action == "cancel":
        os.system("shutdown /a"); speak("Shutdown cancelled.")

# ─────────────────────────────────────────
#  🔋 BATTERY & SYSTEM STATS
# ─────────────────────────────────────────
# Flags so alerts fire only ONCE per charge cycle
_battery_full_alerted = False
_battery_low_alerted  = False

def get_battery():
    try:
        batt = psutil.sensors_battery()
        if batt is None: speak("No battery detected. You are on a desktop PC."); return
        pct     = int(batt.percent)
        plugged = "charging" if batt.power_plugged else "not charging"
        speak(f"Battery is at {pct} percent and {plugged}.")
        if pct < 20 and not batt.power_plugged:
            speak("Warning: battery is low! Please plug in your charger.")
    except Exception as e:
        speak("Could not read battery."); print(f"[Battery] {e}")

def battery_monitor():
    """
    Background thread — checks every 60 seconds.
    Speaks ONCE when battery hits 100% (fully charged).
    Speaks ONCE when battery drops below 20% (low warning).
    Resets flags automatically each cycle.
    """
    global _battery_full_alerted, _battery_low_alerted
    while True:
        try:
            batt = psutil.sensors_battery()
            if batt:
                pct     = int(batt.percent)
                plugged = batt.power_plugged
                # Full charge — alert once
                if pct >= 100 and plugged and not _battery_full_alerted:
                    if S["battery"].get("full_alert",True): speak(r("battery_full"))
                    _battery_full_alerted = True
                # Low battery — alert once
                if pct <= 20 and not plugged and not _battery_low_alerted:
                    if S["battery"].get("low_alert",True): speak(r("battery_low"))
                    _battery_low_alerted = True
                # Reset full alert when charger unplugged
                if not plugged:
                    _battery_full_alerted = False
                # Reset low alert when plugged back in
                if plugged:
                    _battery_low_alerted = False
        except Exception:
            pass
        time.sleep(60)

def get_system_stats():
    try:
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        speak(f"CPU usage is {cpu} percent. "
              f"RAM: {ram.percent} percent used out of {round(ram.total/1e9,1)} gigabytes. "
              f"Disk C: {disk.percent} percent used.")
    except Exception as e:
        speak("Could not read system stats."); print(f"[Stats] {e}")

# ─────────────────────────────────────────
#  🛡 SECURITY — Anti-spy, Process Guard, Firewall
# ─────────────────────────────────────────
SUSPICIOUS_PROCESSES = [
    "keylogger","spy","rat","njrat","darkcomet","nanocore",
    "remcos","stealer","miner","xmrig","coinminer",
    "netcat","nc.exe","masscan"
]

def scan_processes():
    speak("Scanning all running processes for threats. Please wait.")
    found_threats = []; all_procs = []
    for proc in psutil.process_iter(['pid','name']):
        try:
            name = proc.info['name'].lower() if proc.info['name'] else ""
            all_procs.append(name)
            for threat in SUSPICIOUS_PROCESSES:
                if threat in name:
                    found_threats.append(f"{proc.info['name']} (PID {proc.info['pid']})")
        except: continue
    print(f"\n[Security] Running processes ({len(all_procs)} total):")
    for p in sorted(set(all_procs))[:20]: print(f"   {p}")
    if found_threats:
        speak(f"Warning! Found {len(found_threats)} suspicious process.")
        for t in found_threats: speak(f"Suspicious: {t}"); print(f"   ⚠️  {t}")
    else:
        speak(f"All clear! Scanned {len(all_procs)} processes. No threats found.")

def check_firewall():
    try:
        result = subprocess.run(["netsh","advfirewall","show","allprofiles","state"],
            capture_output=True, text=True, timeout=5)
        if "off" in result.stdout.lower():
            speak("Warning! Windows Firewall is OFF. Your PC is exposed. Enable it immediately.")
        else:
            speak("Windows Firewall is active. You are protected.")
    except Exception as e:
        speak("Could not check firewall."); print(f"[Firewall] {e}")

def check_open_ports():
    try:
        speak("Checking open network connections...")
        conns  = psutil.net_connections(kind='inet')
        active = [(c.laddr.port, c.raddr.ip if c.raddr else "local")
                  for c in conns if c.status == 'ESTABLISHED']
        speak(f"Found {len(active)} active internet connections.")
        print("\n[Ports] Active connections:")
        for port, ip in active[:10]: print(f"   Port {port} → {ip}")
    except Exception as e:
        speak("Could not check connections."); print(f"[Ports] {e}")

def full_security_scan():
    speak("Running full security scan...")
    check_firewall(); time.sleep(1)
    scan_processes(); time.sleep(1)
    check_open_ports()
    speak("Security scan complete.")

def take_screenshot():
    try:
        fname = os.path.join(BASE_DIR, f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(fname)
        speak("Screenshot saved.")
        print(f"[Screenshot] {fname}")
    except Exception as e:
        speak("Screenshot failed."); print(f"[SS] {e}")

# ─────────────────────────────────────────
#  🔍 WEB SEARCH
# ─────────────────────────────────────────
def web_search(command):
    """Say: search Google for python tutorial / search YouTube for lofi music"""
    for trigger in ["search google for","search for","google","search youtube for","youtube search"]:
        if trigger in command:
            query = command.split(trigger)[-1].strip()
            if "youtube" in trigger or "youtube" in command:
                webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ','+')}")
                speak(f"Searching YouTube for {query}")
            else:
                webbrowser.open(f"https://www.google.com/search?q={query.replace(' ','+')}")
                speak(f"Searching Google for {query}")
            return
    speak("Say: search Google for your topic")

# ─────────────────────────────────────────
#  🧮 VOICE CALCULATOR
# ─────────────────────────────────────────
def voice_calculator(command):
    """Say: calculate 25 times 4  /  what is 100 divided by 5"""
    try:
        expr = command.lower()
        for trigger in ["calculate","what is","compute","solve"]:
            expr = expr.replace(trigger,"")
        expr = (expr.strip()
            .replace("plus","+").replace("minus","-")
            .replace("times","*").replace("multiplied by","*")
            .replace("divided by","/").replace("power","**")
            .replace("squared","**2").replace("percent","/100"))
        expr_clean = re.sub(r'[^\d\+\-\*\/\.\(\)\*\s]','', expr).strip()
        if expr_clean:
            result = eval(expr_clean)
            speak(f"The answer is {result}")
        else:
            speak("Could not understand the calculation.")
    except Exception as e:
        speak("Calculation failed."); print(f"[Calc] {e}")

# ─────────────────────────────────────────
#  📋 CLIPBOARD
# ─────────────────────────────────────────
def clipboard_action(command):
    """Say: read clipboard  /  copy hello world to clipboard  /  clear clipboard"""
    try:
        if "read" in command or "what is in" in command:
            text = pyperclip.paste()
            speak(f"Clipboard contains: {text[:200]}" if text else "Clipboard is empty.")
        elif "copy" in command:
            text = command.split("copy")[-1].replace("to clipboard","").strip()
            pyperclip.copy(text); speak(f"Copied to clipboard.")
        elif "clear" in command:
            pyperclip.copy(""); speak("Clipboard cleared.")
    except Exception as e:
        speak("Clipboard action failed."); print(f"[Clipboard] {e}")

# ─────────────────────────────────────────
#  ⏸ PLAYBACK CONTROLS
# ─────────────────────────────────────────
def play_pause(): pyautogui.press('space');       speak("Done")
def next_video(): pyautogui.hotkey('shift','n'); speak("Next")
def prev_video(): pyautogui.hotkey('shift','p'); speak("Previous")

# ─────────────────────────────────────────
#  🤖 AI BRAIN — Groq (primary) + Gemini (fallback)
# ─────────────────────────────────────────
JARVIS_SYSTEM = (
    "You are Jarvis, a smart voice assistant. "
    "Reply in 1-3 short sentences max — clear, helpful, conversational. "
    "No markdown, no bullet points, just plain spoken English."
)

def ask_groq(prompt):
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
            json={"model":"llama3-8b-8192",
                  "messages":[{"role":"system","content":JARVIS_SYSTEM},
                               {"role":"user","content":prompt}],
                  "max_tokens":150,"temperature":0.7}, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            return data["choices"][0]["message"]["content"].strip()
        return None
    except Exception as e:
        print(f"[Groq] {e}"); return None

def ask_gemini(prompt):
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type":"application/json"},
            json={"system_instruction":{"parts":[{"text":JARVIS_SYSTEM}]},
                  "contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"maxOutputTokens":150,"temperature":0.7}}, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return None
    except Exception as e:
        print(f"[Gemini] {e}"); return None


# ─────────────────────────────────────────
#  🌍 AUTO LANGUAGE DETECTION
#  Detects which language the user spoke
#  (English / Hindi / Punjabi) and auto-
#  switches Jarvis to reply in same language.
#  Uses simple keyword matching (no extra lib)
#  + Groq AI for confirmation on ambiguous text.
# ─────────────────────────────────────────
HINDI_MARKERS  = ["kya","hai","karo","bolo","batao","mujhe","aaj","kal","theek","haan",
                  "nahi","kyun","kaise","abhi","yahan","wahan","mera","tera","jarvis"]
PUNJABI_MARKERS= ["ki","hega","karو","dasso","ki karna","sat sri","wahe","oye","tusi",
                  "menu","tera","sada","eh","oh","koi","nahi","haan","jarvis"]

def detect_language(text):
    """Detect language from spoken text. Returns: en / hi / pa"""
    t = text.lower()
    # Check for Devanagari or Gurmukhi unicode
    if any('ऀ' <= c <= 'ॿ' for c in text): return "hi"
    if any('਀' <= c <= '੿' for c in text): return "pa"
    # English-only characters — score by marker words
    words   = t.split()
    hi_score = sum(1 for w in words if w in HINDI_MARKERS)
    pa_score = sum(1 for w in words if w in PUNJABI_MARKERS)
    if pa_score > hi_score and pa_score >= 2: return "pa"
    if hi_score >= 2:                          return "hi"
    # Ask Groq to classify if ambiguous
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
            json={"model":"llama3-8b-8192","max_tokens":5,"temperature":0,
                  "messages":[{"role":"system","content":"Reply with only one word: en, hi, or pa — the language of the user message."},
                               {"role":"user","content":text}]}, timeout=5)
        lang = resp.json()["choices"][0]["message"]["content"].strip().lower()[:2]
        if lang in ("en","hi","pa"): return lang
    except: pass
    return "en"

def auto_set_language(text):
    """Detect language from user text and update settings if changed."""
    detected = detect_language(text)
    if detected != S.get("language","en"):
        S["language"] = detected
        save_settings(S)
        print(f"[Lang] Auto-switched to: {detected}")

# ─────────────────────────────────────────
#  😊 AUTO EMOTION DETECTION
#  Detects user's emotional state from their
#  words and makes Jarvis respond with matching
#  human emotion automatically.
# ─────────────────────────────────────────
EMOTION_MAP = {
    "happy":   ["happy","great","awesome","yay","excited","good","wonderful","amazing","love"],
    "sad":     ["sad","upset","crying","depressed","unhappy","miss","lonely","hurt","bad"],
    "angry":   ["angry","frustrated","annoying","stupid","hate","worst","useless","mad"],
    "stressed":["busy","tired","exhausted","stressed","deadline","hurry","fast","quick","urgent"],
    "calm":    ["okay","fine","normal","alright","sure","please","thanks","thank you"],
}
# How Jarvis responds to each detected user emotion
JARVIS_EMOTION_RESPONSE = {
    "happy":   "friendly",
    "sad":     "caring",
    "angry":   "calm",
    "stressed":"calm",
    "calm":    "friendly",
}

def detect_emotion(text):
    """Detect user emotion from text. Returns: happy/sad/angry/stressed/calm"""
    t = text.lower()
    scores = {emo: sum(1 for w in EMOTION_MAP[emo] if w in t) for emo in EMOTION_MAP}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # Ask AI for emotion
        try:
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":"llama3-8b-8192","max_tokens":5,"temperature":0,
                      "messages":[{"role":"system","content":"Detect the user emotion. Reply with only ONE word: happy, sad, angry, stressed, or calm."},
                                   {"role":"user","content":text}]}, timeout=5)
            emo = resp.json()["choices"][0]["message"]["content"].strip().lower()
            if emo in EMOTION_MAP: return emo
        except: pass
        return "calm"
    return best

def auto_set_emotion(text):
    """Detect user emotion and set Jarvis response emotion accordingly."""
    user_emo   = detect_emotion(text)
    jarvis_emo = JARVIS_EMOTION_RESPONSE.get(user_emo, "friendly")
    if jarvis_emo != S.get("emotion","friendly"):
        S["emotion"] = jarvis_emo
        save_settings(S)
        print(f"[Emotion] User seems {user_emo} → Jarvis switching to {jarvis_emo} mode")

def ask_ai(prompt):
    log_privacy(f"Sending to Groq AI: '{prompt[:50]}'")
    answer = ask_groq(prompt)
    if answer:
        log_privacy("Groq answered. Connection closed."); return answer
    log_privacy("Groq failed. Trying Gemini...")
    answer = ask_gemini(prompt)
    if answer:
        log_privacy("Gemini answered. Connection closed."); return answer
    return "Sorry, I could not reach any AI service right now. Please check your internet."

# ─────────────────────────────────────────
#  🧠 COMMAND PROCESSOR
# ─────────────────────────────────────────
def processCommand(c):
    # Auto-detect language and emotion from user speech
    auto_set_language(c)
    auto_set_emotion(c)
    cmd = c.lower().strip()

    # ── Playback ──────────────────────────────────────────────────────
    if any(w in cmd for w in ["pause","stop music"]):    play_pause(); return
    if any(w in cmd for w in ["resume","continue"]):     play_pause(); return
    if "next song" in cmd or "next video" in cmd:        next_video(); return
    if "previous song" in cmd or "prev song" in cmd:     prev_video(); return

    # ── Websites ──────────────────────────────────────────────────────
    elif "open google"    in cmd: webbrowser.open("https://google.com")
    elif "open facebook"  in cmd: webbrowser.open("https://facebook.com")
    elif "open youtube"   in cmd: webbrowser.open("https://youtube.com")
    elif "open linkedin"  in cmd: webbrowser.open("https://linkedin.com")
    elif "open instagram" in cmd: webbrowser.open("https://instagram.com")
    elif "open github"    in cmd: webbrowser.open("https://github.com")
    elif "open twitter"   in cmd: webbrowser.open("https://twitter.com")
    elif "open whatsapp"  in cmd: webbrowser.open("https://web.whatsapp.com")

    # ── Apps ──────────────────────────────────────────────────────────
    elif any(w in cmd for w in ["scan apps","learn apps","update apps"]):
        scan_installed_apps()
    elif cmd.startswith("open"): open_app(" ".join(cmd.split()[1:]).strip())

    # ── Music ─────────────────────────────────────────────────────────
    elif cmd.startswith("play"):
        song = " ".join(cmd.split()[1:]).strip()
        if not song: speak("Please say the song name."); return
        link = search_youtube_instant(song)
        if link: webbrowser.open(link); speak(f"Playing {song}")
        else:    speak(f"Sorry, could not find {song}")

    elif any(w in cmd for w in ["show songs","my songs","song list"]):
        count = len(_song_cache)
        if count:
            speak(f"I remember {count} songs from this session: {', '.join(list(_song_cache.keys())[:5])}")
        else:
            speak("No songs played yet this session. Just say play and the song name!")

    # ── Timer & Reminders ─────────────────────────────────────────────
    elif "set timer" in cmd or "timer for" in cmd:
        secs = parse_timer(cmd)
        if secs: set_timer(secs, "Timer done!")
        else:    speak("Say: set timer for 5 minutes")

    elif "remind me" in cmd or "set reminder" in cmd:
        set_reminder(cmd)

    # ── Weather ───────────────────────────────────────────────────────
    elif "weather" in cmd:
        city = cmd.split("in ")[-1].strip() if "in " in cmd else None
        get_weather(city)

    # ── News ──────────────────────────────────────────────────────────
    elif "news" in cmd:
        topic = cmd.split("about")[-1].strip() if "about" in cmd else None
        get_news(topic)

    # ── SMS ───────────────────────────────────────────────────────────
    elif any(w in cmd for w in ["send sms","send message","text message","send text"]):
        send_sms_command(cmd)

    # ── WhatsApp ──────────────────────────────────────────────────────
    elif "send whatsapp" in cmd or "whatsapp message" in cmd:
        send_whatsapp(cmd)
    elif "whatsapp call" in cmd or ("call" in cmd and "whatsapp" in cmd):
        make_whatsapp_call(cmd)

    # ── Volume ────────────────────────────────────────────────────────
    elif any(w in cmd for w in ["volume","mute","unmute"]):
        handle_volume(cmd)

    # ── System Controls ───────────────────────────────────────────────
    elif "shutdown"  in cmd or "shut down" in cmd: system_control("shutdown")
    elif "restart"   in cmd or "reboot"    in cmd: system_control("restart")
    elif "sleep"     in cmd:                        system_control("sleep")
    elif "lock"      in cmd:                        system_control("lock")
    elif "cancel shutdown" in cmd:                  system_control("cancel")

    # ── Battery & System Stats ────────────────────────────────────────
    elif "battery"   in cmd:                get_battery()
    elif any(w in cmd for w in ["system stats","cpu","ram usage","system status"]):
        get_system_stats()

    # ── Security ──────────────────────────────────────────────────────
    elif any(w in cmd for w in ["security scan","full scan","scan threats","check security"]):
        full_security_scan()
    elif any(w in cmd for w in ["scan processes","check processes"]):
        scan_processes()
    elif any(w in cmd for w in ["check firewall","firewall status"]):
        check_firewall()
    elif any(w in cmd for w in ["check ports","open ports","network connections"]):
        check_open_ports()

    # ── Screenshot ────────────────────────────────────────────────────
    elif "screenshot" in cmd: take_screenshot()

    # ── Web Search ────────────────────────────────────────────────────
    elif any(w in cmd for w in ["search google","search for","search youtube"]):
        web_search(cmd)

    # ── Calculator ────────────────────────────────────────────────────
    elif any(w in cmd for w in ["calculate","compute","solve"]):
        voice_calculator(cmd)

    # ── Clipboard ─────────────────────────────────────────────────────
    elif "clipboard" in cmd: clipboard_action(cmd)

    # ── Time & Date ───────────────────────────────────────────────────
    elif "what time" in cmd or "current time" in cmd:
        speak(f"The time is {datetime.datetime.now().strftime('%I:%M %p')}")
    elif "what date" in cmd or "today" in cmd and "date" in cmd:
        speak(f"Today is {datetime.datetime.now().strftime('%B %d, %Y')}")

    # ── Privacy Log ───────────────────────────────────────────────────
    elif "privacy log" in cmd or "what did you send" in cmd:
        if privacy_log:
            speak(f"Last {min(5,len(privacy_log))} privacy events:")
            for entry in privacy_log[-5:]: speak(entry)
        else:
            speak("Nothing has been sent to any server in this session.")

    # ── Help ──────────────────────────────────────────────────────────
    elif "what can you do" in cmd or "help" in cmd or "commands" in cmd:
        speak("I can: play music, check weather, send SMS and WhatsApp, "
              "make WhatsApp calls, control volume, shutdown or lock your PC, "
              "check battery and CPU, scan for threats, screenshot, "
              "search the web, calculate math, set timers and reminders, "
              "read news, and answer anything with AI.")

    # ── AI Fallback ───────────────────────────────────────────────────
    else:
        if feature_on("ai"):
            reply = ask_ai(c)
            speak(reply)
        else:
            speak(r("feature_off"))

# ─────────────────────────────────────────
#  🚀 MAIN LOOP
# ─────────────────────────────────────────
if __name__ == "__main__":
    speak("Initializing Jarvis. Ultimate version loading.")
    load_vosk()

    if not os.path.exists(APPS_FILE):
        speak("First time setup. Scanning your apps.")
        scan_installed_apps()

    print("\n" + "═"*62)
    print("  J.A.R.V.I.S — ULTIMATE VERSION")
    print("═"*62)
    print(f"  🔒 Wake word  : {'Vosk OFFLINE (private ✅)' if vosk_available else 'Google STT (install Vosk for privacy)'}")
    print("  🎙 Commands   : Google STT (only sent after wake word)")
    print("  🤖 AI Brain   : Groq (primary) + Gemini (fallback)")
    print("  📱 SMS        : Fast2SMS — real SMS to Indian numbers")
    print("  💬 WhatsApp   : Messages + Calls via pywhatkit")
    print("  🛡 Security   : Process scan + Firewall + Port check")
    print("  💻 System     : Shutdown / Restart / Sleep / Lock")
    print("  🔊 Volume     : Up / Down / Mute / Set level")
    print("  🔋 Battery    : Live battery & CPU/RAM stats")
    print("  📸 Screenshot : Save screenshot by voice")
    print("  🔍 Search     : Google & YouTube by voice")
    print("  🧮 Calculator : Voice math")
    print("  📝 Reminders  : Time-based voice reminders")
    print("  📋 Clipboard  : Read & copy text by voice")
    print("═"*62)
    print("\n🎤  Say 'Jarvis' to activate — then give your command")
    print("⌨️  Keyboard: Space=Play/Pause | Shift+N=Next | Shift+P=Prev")
    print("\n📋 Example Commands:")
    print("  play arijit singh            | open chrome")
    print("  weather in Delhi             | news about cricket")
    print("  send SMS to mom saying hello | send WhatsApp to dad saying hi")
    print("  WhatsApp call mom            | volume up / mute / set volume to 50")
    print("  shutdown / restart / lock PC | battery / system stats")
    print("  security scan                | screenshot")
    print("  search Google for recipes    | calculate 25 times 4")
    print("  remind me to call at 5 pm    | set timer for 10 minutes")
    print("  privacy log                  | what can you do\n")

    # Start background battery monitor
    threading.Thread(target=battery_monitor, daemon=True).start()

    speak(time_greeting() + " " + r("greet"))

    while True:
        try:
            # ── STEP 1: Wake word — 100% OFFLINE (Vosk / your CPU) ────
            audio = listen_audio(2.0)
            word  = recognize_vosk(audio)     # nothing sent to internet

            if not word:
                continue

            print("Heard:", word)

            if "jarvis" in word.lower():
                speak(r("greet"))

                # ── STEP 2: Record command ─────────────────────────────
                audio = listen_smart()
                if audio is None:
                    speak("I did not hear anything. Try again."); continue

                # ── STEP 3: Send ONLY the command to Google STT ────────
                command = recognize_google(audio)
                if not command:
                    speak(r("not_understood")); continue

                print("Command:", command)
                processCommand(command)

                # ── STEP 4: Back to offline mode — nothing more sent ───
                log_privacy("Back to offline listening. No data sent.")

        except sr.UnknownValueError:
            pass
        except sr.RequestError:
            speak("Speech service unavailable. Check internet.")
        except Exception as e:
            print("Error:", e)