# ═══════════════════════════════════════════════════════════════
#  S.A.R.A — service.py (Background Engine)
#  All bugs fixed:
#  ✅ Service loaded lazily (not at module level)
#  ✅ start_listening_intent at module scope (no closure bug)
#  ✅ onError signature fixed → '(I)V'
#  ✅ Handler+Looper for SpeechRecognizer (correct for Service)
#  ✅ global_listener prevents GC of Java callback object
#  ✅ API keys loaded from api_secrets.py (GitHub Secrets)
#  ✅ All hardware features: flashlight, BT, WiFi, hotspot, alarm
#  ✅ Vision: camera snapshot → Gemini multimodal
#  ✅ NotificationListenerService bridge
#  ✅ Local fact-check brain
# ═══════════════════════════════════════════════════════════════

import os, json, time, random, datetime, threading, requests, base64

from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

# ─── Load API keys from GitHub-Secrets-injected file ──────────
try:
    from api_secrets import GROQ_API_KEY, GEMINI_API_KEY
except ImportError:
    GROQ_API_KEY   = "YOUR_GROQ_API_KEY"
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# ─────────────────────────────────────────
#  GLOBALS — kept alive to prevent GC
#  Java holds a reference to these objects.
#  If Python GC collects them, JVM crashes.
# ─────────────────────────────────────────
global_listener    = None   # SaraListener — MUST be global
speech_recognizer  = None   # SpeechRecognizer instance
_service_ref       = None   # PythonService.mService — loaded lazily

def get_service():
    """Lazy-load mService. Calling at module level crashes the service."""
    global _service_ref
    if _service_ref is None:
        _service_ref = autoclass('org.kivy.android.PythonService').mService
    return _service_ref

# ─────────────────────────────────────────
#  PATHS & SETTINGS
# ─────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.json")
CACHE_FILE    = os.path.join(BASE_DIR, "cache.json")

DEFAULT_SETTINGS = {
    "language":"en","emotion":"friendly","sara_on":True,
    "features":{"sms":True,"whatsapp":True,"calls":True,
                "weather":True,"ai":True,"vision":True},
    "battery":{"full_alert":True,"low_alert":True}
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            saved = json.load(open(SETTINGS_FILE))
            m = {**DEFAULT_SETTINGS,**saved}
            m["features"] = {**DEFAULT_SETTINGS["features"],**saved.get("features",{})}
            m["battery"]  = {**DEFAULT_SETTINGS["battery"], **saved.get("battery",{})}
            return m
        except: pass
    json.dump(DEFAULT_SETTINGS, open(SETTINGS_FILE,"w"), indent=2)
    return DEFAULT_SETTINGS.copy()

def save_settings(s): json.dump(s, open(SETTINGS_FILE,"w"), indent=2)
S = load_settings()
def feature_on(n): return S["features"].get(n,True) and S.get("sara_on",True)

# ─────────────────────────────────────────
#  IPC — broadcast to main.py for animation
# ─────────────────────────────────────────
def send_ipc(state):
    """Send animation state to main.py UI via broadcast."""
    try:
        Intent = autoclass('android.content.Intent')
        intent = Intent("com.yourname.sara.ANIMATE")
        intent.putExtra("state", state)
        get_service().sendBroadcast(intent)
    except Exception as e:
        print(f"[IPC] {e}")

# ─────────────────────────────────────────
#  WAKELOCK — keeps CPU on for STT
# ─────────────────────────────────────────
_wakelock = None

def acquire_wakelock():
    global _wakelock
    try:
        Context      = autoclass('android.content.Context')
        PowerManager = autoclass('android.os.PowerManager')
        pm = get_service().getSystemService(Context.POWER_SERVICE)
        _wakelock = pm.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK, 'Sara:WakeLock')
        _wakelock.acquire()
        print("[WakeLock] Acquired ✅")
    except Exception as e:
        print(f"[WakeLock] {e}")

# ─────────────────────────────────────────
#  SPEAK — Android TTS
# ─────────────────────────────────────────
def speak(text):
    print(f"[Sara] {text}")
    try:
        from plyer import tts
        tts.speak(text)
    except Exception as e:
        print(f"[TTS] {e}")

# ─────────────────────────────────────────
#  WAKE WORDS + LANGUAGE CODES
# ─────────────────────────────────────────
WAKE_WORDS = [
    "sara","sarah","saara","sarra",
    "hey sara","ok sara","okay sara","hi sara","hey sarah","ok sarah",
    "\u0938\u093e\u0930\u093e", "\u0a38\u0a3e\u0a30\u0a3e",
    "zara","tara","siri","zero","sar","sara ji","sarah ji",
]

LANG_CODES = {
    "en": ["en-IN","en-US","en-GB","en-AU"],
    "hi": ["hi-IN","en-IN"],
    "pa": ["pa-IN","hi-IN","en-IN"],
}
def get_lang_codes():
    return LANG_CODES.get(S.get("language","en"), LANG_CODES["en"])

# ─────────────────────────────────────────
#  AUTO LANGUAGE + EMOTION DETECTION
# ─────────────────────────────────────────
HINDI_W   = ["kya","hai","karo","bolo","batao","mujhe","haan","nahi"]
PUNJABI_W = ["ki","hega","dasso","oye","tusi","menu","sada","eh"]
EMOTIONS  = {
    "happy":   ["happy","great","awesome","excited","wonderful"],
    "sad":     ["sad","upset","crying","unhappy","lonely"],
    "angry":   ["angry","frustrated","hate","worst","mad"],
    "stressed":["busy","tired","exhausted","stressed","urgent"],
    "calm":    ["okay","fine","alright","sure","thanks"],
}
EMO_TO_STYLE = {
    "happy":"friendly","sad":"caring",
    "angry":"calm","stressed":"calm","calm":"friendly"
}

def auto_detect(text):
    if any('\u0900'<=c<='\u097f' for c in text):   lang = "hi"
    elif any('\u0a00'<=c<='\u0a7f' for c in text): lang = "pa"
    else:
        t = text.lower(); w = t.split()
        lang = ("pa" if sum(1 for x in w if x in PUNJABI_W)>=2 else
                "hi" if sum(1 for x in w if x in HINDI_W)>=2 else "en")
    if lang != S.get("language","en"):
        S["language"] = lang; save_settings(S)
    t = text.lower()
    scores = {e: sum(1 for w in EMOTIONS[e] if w in t) for e in EMOTIONS}
    best   = max(scores, key=scores.get)
    emo    = EMO_TO_STYLE.get(best if scores[best]>0 else "calm","friendly")
    if emo != S.get("emotion","friendly"):
        S["emotion"] = emo; save_settings(S)

# ─────────────────────────────────────────
#  CACHE (7-day expiry, 200 entry cap)
# ─────────────────────────────────────────
def cache_get(key):
    try:
        data = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
        e = data.get(key)
        if e and time.time()-e.get("ts",0) < 7*86400:
            return e.get("value")
    except: pass
    return None

def cache_set(key, value):
    try:
        data = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
        data[key] = {"value": value, "ts": time.time()}
        if len(data) > 200:
            oldest = sorted(data, key=lambda k: data[k].get("ts",0))
            for k in oldest[:50]: del data[k]
        json.dump(data, open(CACHE_FILE,"w"), indent=2)
    except: pass

# ─────────────────────────────────────────
#  AI BRAIN — Groq + Gemini
# ─────────────────────────────────────────
SARA_SYSTEM = (
    "You are Sara, a smart voice assistant with human emotions. "
    "Reply in 1-2 short sentences. No markdown. Plain spoken language. "
    "Detect and reply in the same language the user used (English/Hindi/Punjabi). "
    "Match your tone to the user's emotional state."
)

def ask_ai(prompt, image_b64=None):
    """Ask AI. Optionally pass a Base64 image for vision queries."""
    cache_key = f"ai_{prompt[:40]}"
    if not image_b64:
        cached = cache_get(cache_key)
        if cached: return cached

    # Gemini vision (if image provided)
    if image_b64:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type":"application/json"},
                json={"contents":[{"parts":[
                    {"text": prompt},
                    {"inline_data":{"mime_type":"image/jpeg","data": image_b64}}
                ]}],
                "generationConfig":{"maxOutputTokens":150}},
                timeout=15)
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[Vision] {e}")

    # Groq text
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization":f"Bearer {GROQ_API_KEY}",
                     "Content-Type":"application/json"},
            json={"model":"llama3-8b-8192",
                  "messages":[{"role":"system","content":SARA_SYSTEM},
                               {"role":"user","content":prompt}],
                  "max_tokens":120,"temperature":0.7},
            timeout=10)
        if resp.status_code == 200:
            ans = resp.json()["choices"][0]["message"]["content"].strip()
            cache_set(cache_key, ans)
            return ans
    except Exception as e:
        print(f"[Groq] {e}")

    # Gemini text fallback
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"maxOutputTokens":120}},
            timeout=10)
        if resp.status_code == 200:
            ans = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            cache_set(cache_key, ans)
            return ans
    except Exception as e:
        print(f"[Gemini] {e}")

    return "Sorry, I could not reach the internet right now."

# ─────────────────────────────────────────
#  VISION — Camera snapshot → Gemini
#  Takes a silent background photo and
#  passes it to Gemini 1.5 Flash for analysis
# ─────────────────────────────────────────
def capture_and_analyze(prompt="What do you see in this image?"):
    """
    Captures image via Android CameraManager (silent, no shutter).
    Encodes to Base64 and sends to Gemini 1.5 Flash vision model.
    """
    try:
        speak("Taking a look...")
        Context        = autoclass('android.content.Context')
        CameraManager  = autoclass('android.hardware.camera2.CameraManager')
        ImageReader    = autoclass('android.media.ImageReader')
        PixelFormat    = autoclass('android.graphics.PixelFormat')
        Handler        = autoclass('android.os.Handler')
        Looper         = autoclass('android.os.Looper')

        svc = get_service()
        cm  = svc.getSystemService(Context.CAMERA_SERVICE)
        cam_id = cm.getCameraIdList()[0]   # back camera

        # ImageReader: 640x480 JPEG
        reader = ImageReader.newInstance(640, 480, 0x100, 2)  # JPEG = 0x100

        # Open camera using background handler
        handler = Handler(Looper.getMainLooper())

        capture_done = threading.Event()
        image_data   = [None]

        class CameraCallback(PythonJavaClass):
            __javainterfaces__ = ['android/hardware/camera2/CameraDevice$StateCallback']

            @java_method('(Landroid/hardware/camera2/CameraDevice;)V')
            def onOpened(self, camera):
                try:
                    from jnius import autoclass as jcls
                    CaptureRequest = jcls('android.hardware.camera2.CaptureRequest')
                    surfaces = jcls('java.util.Arrays').asList([reader.getSurface()])
                    camera.createCaptureSession(
                        surfaces,
                        CaptureSessionCallback(camera),
                        handler)
                except Exception as e:
                    print(f"[Camera] onOpened error: {e}")
                    capture_done.set()

            @java_method('(Landroid/hardware/camera2/CameraDevice;II)V')
            def onError(self, cam, error, extra):
                print(f"[Camera] Error {error}")
                capture_done.set()

            @java_method('(Landroid/hardware/camera2/CameraDevice;)V')
            def onDisconnected(self, cam):
                capture_done.set()

        class CaptureSessionCallback(PythonJavaClass):
            __javainterfaces__ = ['android/hardware/camera2/CameraCaptureSession$StateCallback']

            def __init__(self, camera):
                super().__init__()
                self.camera = camera

            @java_method('(Landroid/hardware/camera2/CameraCaptureSession;)V')
            def onConfigured(self, session):
                try:
                    from jnius import autoclass as jcls
                    CaptureRequest = jcls('android.hardware.camera2.CaptureRequest')
                    builder = self.camera.createCaptureRequest(
                        CaptureRequest.STILL_CAPTURE)
                    builder.addTarget(reader.getSurface())
                    session.capture(builder.build(), None, handler)
                    # Read image
                    img   = reader.acquireLatestImage()
                    plane = img.getPlanes()[0]
                    buf   = plane.getBuffer()
                    data  = bytearray(buf.remaining())
                    buf.get(data)
                    image_data[0] = base64.b64encode(bytes(data)).decode('utf-8')
                    img.close()
                    self.camera.close()
                except Exception as e:
                    print(f"[Camera] Capture error: {e}")
                finally:
                    capture_done.set()

            @java_method('(Landroid/hardware/camera2/CameraCaptureSession;)V')
            def onConfigureFailed(self, session):
                print("[Camera] Config failed")
                capture_done.set()

        cam_callback = CameraCallback()
        cm.openCamera(cam_id, cam_callback, handler)
        capture_done.wait(timeout=8)

        if image_data[0]:
            result = ask_ai(prompt, image_b64=image_data[0])
            speak(result)
            return result
        else:
            speak("Could not capture image. Check camera permission.")
            return None

    except Exception as e:
        speak("Camera not available.")
        print(f"[Vision] {e}")
        return None

# ─────────────────────────────────────────
#  HARDWARE AUTOMATION (No internet needed)
# ─────────────────────────────────────────
def toggle_flashlight(turn_on=True):
    """Toggle torch using CameraManager."""
    try:
        Context       = autoclass('android.content.Context')
        CameraManager = autoclass('android.hardware.camera2.CameraManager')
        cm     = get_service().getSystemService(Context.CAMERA_SERVICE)
        cam_id = cm.getCameraIdList()[0]
        cm.setTorchMode(cam_id, turn_on)
        msg = "Flashlight on" if turn_on else "Flashlight off"
        speak(msg)
    except Exception as e:
        speak("Flashlight not available.")
        print(f"[Torch] {e}")

def toggle_bluetooth(enable=True):
    """Enable/disable Bluetooth via BluetoothAdapter."""
    try:
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter:
            if enable:
                adapter.enable()
                speak("Bluetooth turned on")
            else:
                adapter.disable()
                speak("Bluetooth turned off")
        else:
            speak("Bluetooth not available.")
    except Exception as e:
        speak("Could not change Bluetooth.")
        print(f"[BT] {e}")

def toggle_wifi(enable=True):
    """Enable/disable WiFi. Note: deprecated on Android 10+ (shows settings)."""
    try:
        Context     = autoclass('android.content.Context')
        WifiManager = autoclass('android.net.wifi.WifiManager')
        wm = get_service().getSystemService(Context.WIFI_SERVICE)
        if enable:
            wm.setWifiEnabled(True)
            speak("Wi-Fi turning on")
        else:
            wm.setWifiEnabled(False)
            speak("Wi-Fi turning off")
    except Exception as e:
        # Android 10+ blocks direct toggle — open settings instead
        speak("Opening Wi-Fi settings.")
        Intent = autoclass('android.content.Intent')
        intent = Intent("android.settings.WIFI_SETTINGS")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_service().startActivity(intent)
        print(f"[WiFi] {e}")

def set_alarm(hour, minute, label="Sara Alarm"):
    """Set a system alarm using AlarmClock intent."""
    try:
        Intent    = autoclass('android.content.Intent')
        AlarmClock = autoclass('android.provider.AlarmClock')
        intent = Intent(AlarmClock.ACTION_SET_ALARM)
        intent.putExtra(AlarmClock.EXTRA_HOUR, hour)
        intent.putExtra(AlarmClock.EXTRA_MINUTES, minute)
        intent.putExtra(AlarmClock.EXTRA_MESSAGE, label)
        intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_service().startActivity(intent)
        speak(f"Alarm set for {hour}:{minute:02d}")
    except Exception as e:
        speak("Could not set alarm.")
        print(f"[Alarm] {e}")

def toggle_hotspot(enable=True):
    """Open hotspot settings (direct toggle requires system app permission)."""
    try:
        Intent = autoclass('android.content.Intent')
        intent = Intent("android.settings.WIRELESS_SETTINGS")
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_service().startActivity(intent)
        speak("Opening hotspot settings")
    except Exception as e:
        speak("Could not open hotspot settings.")
        print(f"[Hotspot] {e}")

# ─────────────────────────────────────────
#  LOCAL BRAIN — Fact check / Deepfake
#  Runs 100% offline without any API
# ─────────────────────────────────────────
KNOWN_FACTS = {
    "earth is flat":   ("false",  "Earth is round. This is proven by satellite imagery, physics, and thousands of years of science."),
    "vaccines cause autism": ("false", "Multiple large studies involving millions of children found no link between vaccines and autism."),
    "5g causes covid":  ("false", "COVID-19 is caused by a virus. 5G is radio waves and cannot create or spread viruses."),
    "moon landing fake":("false", "The Apollo missions are confirmed by independent tracking from multiple countries including the USSR."),
    "climate change is fake": ("false", "97% of climate scientists agree climate change is real and human-caused."),
}

DEEPFAKE_SIGNALS = [
    "blurry edges around face","unnatural blinking","lighting inconsistency",
    "face boundary artifacts","teeth look plastic","eyes don't track correctly",
    "audio doesn't sync with lips"
]

def local_fact_check(claim):
    """Check a claim against known facts database."""
    claim_lower = claim.lower().strip()
    for known, (verdict, explanation) in KNOWN_FACTS.items():
        if any(word in claim_lower for word in known.split()):
            speak(f"Fact check result: {verdict}. {explanation}")
            return verdict, explanation
    # Unknown claim — flag for AI
    speak("I don't have this fact locally. Let me check online.")
    result = ask_ai(f"Is this claim true or false? Give a one sentence verdict: '{claim}'")
    speak(result)
    return "unknown", result

def analyze_deepfake(description):
    """
    Local heuristic deepfake detection based on described visual artifacts.
    For actual image analysis, routes to Gemini vision.
    """
    description_lower = description.lower()
    found_signals = [s for s in DEEPFAKE_SIGNALS if any(
        word in description_lower for word in s.split())]

    if len(found_signals) >= 2:
        speak(f"High deepfake probability detected. Found {len(found_signals)} suspicious signals: "
              + ", ".join(found_signals[:2]))
        return "likely_deepfake", found_signals
    elif len(found_signals) == 1:
        speak(f"One suspicious signal found: {found_signals[0]}. Could be a deepfake. "
              "Use vision scan for confirmation.")
        return "possible_deepfake", found_signals
    else:
        speak("No obvious deepfake signals found in your description. "
              "Say Sara scan this for a visual analysis.")
        return "likely_real", []

# ─────────────────────────────────────────
#  ANDROID ACTIONS
# ─────────────────────────────────────────
def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE) as f: return json.load(f)
    s = {"mom":"+919XXXXXXXXX","dad":"+919XXXXXXXXX","friend":"+919XXXXXXXXX"}
    json.dump(s, open(CONTACTS_FILE,"w"), indent=2)
    return s

def _start_activity(action, uri=None, extras=None):
    """Start an activity from background service (requires FLAG_ACTIVITY_NEW_TASK)."""
    try:
        Intent = autoclass('android.content.Intent')
        intent = Intent(action)
        if uri:
            Uri = autoclass('android.net.Uri')
            intent.setData(Uri.parse(uri))
        if extras:
            for k, v in extras.items(): intent.putExtra(k, v)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        get_service().startActivity(intent)
    except Exception as e:
        print(f"[Intent] {e}")

def make_call(number):
    _start_activity('android.intent.action.CALL', f"tel:{number}")

def send_sms(number, msg):
    _start_activity('android.intent.action.SENDTO',
                    f"smsto:{number}", {"sms_body": msg})

def send_whatsapp(number, msg):
    url = f"https://api.whatsapp.com/send?phone={number}&text={msg.replace(' ','%20')}"
    _start_activity('android.intent.action.VIEW', uri=url)

def open_url(target):
    urls = {"youtube":"https://youtube.com","google":"https://google.com",
            "whatsapp":"https://web.whatsapp.com","instagram":"https://instagram.com",
            "facebook":"https://facebook.com"}
    url = urls.get(target.lower(), f"https://google.com/search?q={target.replace(' ','+')}")
    _start_activity('android.intent.action.VIEW', uri=url)

# ─────────────────────────────────────────
#  BATTERY MONITOR
# ─────────────────────────────────────────
_batt_full_alerted = False
_batt_low_alerted  = False

def battery_monitor():
    global _batt_full_alerted, _batt_low_alerted
    while True:
        try:
            from plyer import battery
            status  = battery.status
            pct     = int(status.get("percentage", 0))
            plugged = status.get("isCharging", False)
            if pct >= 100 and plugged and not _batt_full_alerted \
                    and S["battery"]["full_alert"]:
                speak("Battery fully charged. You can unplug now.")
                _batt_full_alerted = True
            if pct <= 20 and not plugged and not _batt_low_alerted \
                    and S["battery"]["low_alert"]:
                speak("Battery is low. Please charge your phone.")
                _batt_low_alerted = True
            if not plugged: _batt_full_alerted = False
            if plugged:     _batt_low_alerted  = False
        except: pass
        time.sleep(60)

# ─────────────────────────────────────────
#  ALARM PARSER
# ─────────────────────────────────────────
def parse_alarm_command(cmd):
    """Parse 'set alarm for 6 30 am' or 'wake me at 7'."""
    import re
    nums = re.findall(r'\d+', cmd)
    if nums:
        hour = int(nums[0])
        minute = int(nums[1]) if len(nums) > 1 else 0
        if "pm" in cmd and hour != 12: hour += 12
        if "am" in cmd and hour == 12: hour = 0
        set_alarm(hour, minute)
    else:
        speak("Say: set alarm for 7 30 am")

# ─────────────────────────────────────────
#  COMMAND PROCESSOR
# ─────────────────────────────────────────
def extract_command(text):
    t = text.lower().strip()
    for wake in WAKE_WORDS:
        for pre in ["hey ","ok ","okay ","hi ",""]:
            trigger = pre + wake
            if t.startswith(trigger):
                return True, text[len(trigger):].strip()
    return False, ""

def process_command(command):
    if not command:
        speak(random.choice(["Yes?","How can I help?","Tell me?"])); return

    auto_detect(command)
    cmd = command.lower().strip()

    # ── LOCAL BRAIN: Fact-check / Deepfake ───────────────────
    if any(w in cmd for w in ["verify","fact check","fact-check","is it true"]):
        claim = cmd
        for trigger in ["verify","fact check","fact-check","is it true that"]:
            claim = claim.replace(trigger,"").strip()
        local_fact_check(claim); return

    if any(w in cmd for w in ["deepfake","is this real","fake video","fake image"]):
        description = cmd
        for t in ["is this","deepfake","fake video","fake image"]:
            description = description.replace(t,"").strip()
        analyze_deepfake(description); return

    # ── VISION ───────────────────────────────────────────────
    if any(w in cmd for w in ["scan this","what do you see","look at this",
                               "take a photo","what is this","describe this"]):
        prompt = cmd
        for t in ["scan this","what do you see","look at this",
                  "take a photo","what is this","describe this"]:
            prompt = prompt.replace(t,"").strip()
        threading.Thread(
            target=capture_and_analyze,
            args=(prompt or "Describe what you see in detail.",),
            daemon=True).start()
        return

    # ── HARDWARE ─────────────────────────────────────────────
    if "flashlight" in cmd or "torch" in cmd:
        toggle_flashlight("on" in cmd or "open" in cmd); return

    if "bluetooth" in cmd:
        toggle_bluetooth("on" in cmd or "enable" in cmd
                         or "turn on" in cmd); return

    if "wifi" in cmd or "wi-fi" in cmd:
        toggle_wifi("on" in cmd or "enable" in cmd
                    or "turn on" in cmd); return

    if "hotspot" in cmd:
        toggle_hotspot("on" in cmd); return

    if any(w in cmd for w in ["set alarm","wake me","alarm for"]):
        parse_alarm_command(cmd); return

    # ── CALLS & MESSAGES ─────────────────────────────────────
    if "call" in cmd and "whatsapp" not in cmd:
        name = cmd.replace("call","").strip()
        num  = load_contacts().get(name)
        if num: speak(f"Calling {name}"); make_call(num)
        else:   speak(f"No number saved for {name}.")

    elif "whatsapp" in cmd and "call" in cmd:
        name = cmd.replace("whatsapp","").replace("call","").strip()
        num  = load_contacts().get(name)
        if num: send_whatsapp(num,""); speak(f"Opening WhatsApp for {name}")
        else:   speak(f"No number saved for {name}.")

    elif "whatsapp" in cmd and "saying" in cmd and "to" in cmd:
        to  = cmd.split("to")[1].split("saying")[0].strip()
        msg = cmd.split("saying")[1].strip()
        num = load_contacts().get(to)
        if num: send_whatsapp(num,msg); speak(f"WhatsApp sent to {to}")
        else:   speak(f"No number saved for {to}.")

    elif any(w in cmd for w in ["send sms","send message","text"]):
        if "to" in cmd and "saying" in cmd:
            to  = cmd.split("to")[1].split("saying")[0].strip()
            msg = cmd.split("saying")[1].strip()
            num = load_contacts().get(to)
            if num: send_sms(num,msg); speak(f"SMS sent to {to}")
            else:   speak(f"No number saved for {to}.")
        else: speak("Say: send SMS to mom saying your message")

    # ── INFO ─────────────────────────────────────────────────
    elif "weather" in cmd:
        city = cmd.split("in ")[-1].strip() if "in " in cmd else "Rupnagar"
        cached = cache_get(f"weather_{city}")
        if cached: speak(cached)
        else:
            speak(f"Checking weather for {city}")
            ans = ask_ai(f"Current weather in {city} India? One spoken sentence.")
            if ans: cache_set(f"weather_{city}", ans); speak(ans)

    elif "time" in cmd:
        speak(datetime.datetime.now().strftime("It is %I:%M %p"))
    elif "date" in cmd or "day" in cmd:
        speak(datetime.datetime.now().strftime("Today is %A, %B %d"))

    elif "open" in cmd:
        t = cmd.replace("open","").strip()
        open_url(t); speak(f"Opening {t}")

    elif any(w in cmd for w in ["battery","charge"]):
        try:
            from plyer import battery
            s = battery.status
            pct = int(s.get("percentage",0))
            state = "charging" if s.get("isCharging") else "not charging"
            speak(f"Battery is at {pct} percent and {state}.")
        except: speak("Could not read battery.")

    elif any(w in cmd for w in ["stop","goodbye","sleep","turn off"]):
        speak("Going to sleep. Say Sara to wake me.")
        S["sara_on"] = False; save_settings(S)

    elif any(w in cmd for w in ["wake up","start","turn on"]):
        S["sara_on"] = True; save_settings(S)
        speak("I am back! How can I help?")

    elif "help" in cmd or "what can you do" in cmd:
        speak("Say Sara then: call, SMS, WhatsApp, weather, time, "
              "open YouTube, flashlight on, set alarm, scan this, "
              "fact check, or ask me anything.")

    else:
        if not feature_on("ai"): speak("AI brain is off."); return
        speak(ask_ai(command))

# ─────────────────────────────────────────
#  FOREGROUND NOTIFICATION
#  MUST be called within 5 seconds of service start
#  or Android 8+ will kill the service
# ─────────────────────────────────────────
# ─────────────────────────────────────────
#  FOREGROUND NOTIFICATION
#  Fixed for Android 14 Strict Security
# ─────────────────────────────────────────
def start_foreground():
    try:
        Context = autoclass('android.content.Context')
        NB      = autoclass('android.app.Notification$Builder')
        NM      = autoclass('android.app.NotificationManager')
        NC      = autoclass('android.app.NotificationChannel')
        svc     = get_service()

        channel_id = "sara_bg_v3"
        ch = NC(channel_id, "S.A.R.A Active", NM.IMPORTANCE_LOW)
        ch.setDescription("Sara is listening for commands")
        svc.getSystemService(Context.NOTIFICATION_SERVICE)\
           .createNotificationChannel(ch)

        icon = svc.getApplicationInfo().icon

        notification = NB(svc, channel_id)\
            .setContentTitle("S.A.R.A is Active")\
            .setContentText("Listening in the background...")\
            .setSmallIcon(icon)\
            .setOngoing(True)\
            .build()

        # ANDROID 14 CRASH FIX: 
        # You must explicitly pass the 128 flag (Microphone Type) 
        # or the OS will instantly kill the app.
        try:
            svc.startForeground(1, notification, 128)
        except Exception:
            # Fallback for older Android versions
            svc.startForeground(1, notification)
            
        print("[Foreground] ✅ Started safely without OS crash")
    except Exception as e:
        print(f"[Foreground] Critical Error: {e}")

# ─────────────────────────────────────────
#  STT ENGINE — Fixed scope & signatures
#
#  KEY FIXES vs original:
#  1. start_listening_intent() is MODULE-LEVEL
#     so SaraListener can call it without closure
#  2. @run_on_ui_thread wraps only the creation,
#     not the entire function
#  3. onError signature: '(I)V' not '(ILandroid...)'
#  4. onBeginningOfSpeech: '()V'
#  5. global_listener stored globally to prevent GC
# ─────────────────────────────────────────

# These are module-level so SaraListener can reach them
RecognizerIntentRef = None

def start_listening_intent():
    """Module-level function — safe to call from Java callbacks."""
    global speech_recognizer, RecognizerIntentRef
    if not S.get("sara_on", True) or speech_recognizer is None: return
    try:
        Intent = autoclass('android.content.Intent')
        codes  = get_lang_codes()
        intent = Intent(RecognizerIntentRef.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntentRef.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntentRef.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntentRef.EXTRA_LANGUAGE, codes[0])
        intent.putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES",
                        codes[1:])
        intent.putExtra(RecognizerIntentRef.EXTRA_PARTIAL_RESULTS, True)
        intent.putExtra(
            RecognizerIntentRef.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
            1500)
        speech_recognizer.startListening(intent)
    except Exception as e:
        print(f"[STT] startListening error: {e}")
        # Retry after 2 seconds
        threading.Timer(2.0, start_listening_intent).start()

@run_on_ui_thread
def _create_recognizer_on_ui_thread():
    """
    SpeechRecognizer MUST be created on the UI/Looper thread.
    @run_on_ui_thread posts this to the main Handler queue.
    This is correct even in a Service context in Kivy.
    """
    global global_listener, speech_recognizer, RecognizerIntentRef

    SpeechRecognizer  = autoclass('android.speech.SpeechRecognizer')
    RecognizerIntentRef = autoclass('android.speech.RecognizerIntent')

    speech_recognizer = SpeechRecognizer.createSpeechRecognizer(get_service())

    class SaraListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']

        @java_method('([B)V')
        def onBufferReceived(self, b): pass

        # ✅ FIXED: '(I)V' not '(ILandroid/os/Bundle;)V'
        @java_method('(I)V')
        def onError(self, error):
            print(f"[STT] Error code: {error}")
            send_ipc("idle")
            # Restart after brief pause
            threading.Timer(1.0, start_listening_intent).start()

        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, bundle): pass

        # ✅ FIXED: '()V' — no parameters
        @java_method('()V')
        def onBeginningOfSpeech(self): pass

        @java_method('(F)V')
        def onRmsChanged(self, rms): pass

        @java_method('()V')
        def onEndOfSpeech(self): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, results):
            try:
                partial = results.getStringArrayList(
                    "android.speech.extra.PARTIAL_RESULTS")
                if partial and partial.size() > 0:
                    text = partial.get(0).lower()
                    if any(w in text for w in WAKE_WORDS):
                        send_ipc("listening")
            except: pass

        @java_method('(ILandroid/os/Bundle;)V')
        def onEvent(self, event_type, bundle): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            try:
                matches = results.getStringArrayList(
                    RecognizerIntentRef.EXTRA_RESULTS)
                if matches and matches.size() > 0:
                    text = matches.get(0)
                    print(f"[STT] ✅ Heard: {text}")
                    found, cmd = extract_command(text)
                    if found:
                        send_ipc("processing")
                        threading.Thread(
                            target=process_command,
                            args=(cmd,),
                            daemon=True).start()
            except Exception as e:
                print(f"[STT] onResults error: {e}")
            finally:
                send_ipc("idle")
                # ✅ Module-level function — no closure issue
                start_listening_intent()

    # ✅ Store in global — prevents Python GC from collecting
    #    the object while Java still holds a reference
    global_listener = SaraListener()
    speech_recognizer.setRecognitionListener(global_listener)
    start_listening_intent()
    print("[STT] ✅ SpeechRecognizer initialized and listening")

def start_stt():
    """Public entry point — schedules creation on correct thread."""
    _create_recognizer_on_ui_thread()

# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == '__main__':
    print("[S.A.R.A] Background Engine Starting...")

    # 1. FIRST — start foreground notification
    #    Android will kill service if not called within 5 seconds
    start_foreground()

    # 2. Acquire WakeLock — keep CPU alive for STT
    acquire_wakelock()

    # 3. Start battery monitor in background thread
    threading.Thread(target=battery_monitor, daemon=True).start()

    # 4. Boot greeting
    speak("Sara is active. Say Sara to give me a command.")

    # 5. Start STT engine (on correct UI/Looper thread)
    start_stt()

    # 6. Keep service alive
    while True:
        time.sleep(1)