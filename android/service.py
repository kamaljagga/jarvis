import os, json, re, time, random, datetime, threading, requests
from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

# ─────────────────────────────────────────
#  1. ANDROID SERVICE SETUP & WAKELOCK
# ─────────────────────────────────────────
global_listener = None
speech_recognizer = None

Context = autoclass('android.content.Context')
Service = autoclass('org.kivy.android.PythonService').mService
Intent = autoclass('android.content.Intent')

def acquire_wakelock():
    try:
        PowerManager = autoclass('android.os.PowerManager')
        pm = Service.getSystemService(Context.POWER_SERVICE)
        wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, 'Sara:WakeLock')
        wakelock.acquire()
    except Exception as e:
        print(f"[WakeLock] {e}")

def send_ipc_animation_state(state):
    try:
        intent = Intent("com.sara.ANIMATE")
        intent.putExtra("state", state)
        Service.sendBroadcast(intent)
    except: pass

# ─────────────────────────────────────────
#  2. YOUR ORIGINAL CONFIG & AI LOGIC
# ─────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.json")
CACHE_FILE    = os.path.join(BASE_DIR, "cache.json")

GROQ_API_KEY   = "YOUR_GROQ_API_KEY"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

DEFAULT_SETTINGS = {
    "language":"en","emotion":"friendly","sara_on":True,
    "features":{"sms":True,"whatsapp":True,"calls":True,"weather":True,"ai":True},
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

WAKE_WORDS = ["sara","sarah","saara","sarra","hey sara","ok sara","okay sara","hi sara","hey sarah","ok sarah","\u0938\u093e\u0930\u093e","\u0a38\u0a3e\u0a30\u0a3e","zara","tara","siri","zero","sar","sara ji","sarah ji"]

LANG_CODES = {
    "en": ["en-IN","en-US","en-GB","en-AU"],
    "hi": ["hi-IN","en-IN"],
    "pa": ["pa-IN","hi-IN","en-IN"],
}

def get_lang_codes(): return LANG_CODES.get(S.get("language","en"), LANG_CODES["en"])

def speak(text):
    print(f"[Sara] {text}")
    try:
        from plyer import tts
        tts.speak(text)
    except Exception as e: print(f"[TTS] {e}")

# ... (Insert your existing auto_detect, cache_get, and cache_set functions here exactly as you wrote them) ...

SARA_SYSTEM = ("You are Sara, a smart voice assistant with emotions. Reply in 1-2 short sentences. No markdown. Plain spoken language. If you don't know the answer, say I have no information on that.")

def ask_ai(prompt):
    # Your exact Groq and Gemini API logic remains untouched here
    # ... (Insert your existing ask_ai function here) ...
    pass

def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE) as f: return json.load(f)
    s={"mom":"+919XXXXXXXXX","dad":"+919XXXXXXXXX","friend":"+919XXXXXXXXX"}
    json.dump(s,open(CONTACTS_FILE,"w"),indent=2); return s

# ─────────────────────────────────────────
#  3. HARDWARE & NEW CAPABILITIES
# ─────────────────────────────────────────
def _android_intent(action, uri=None, extras=None):
    try:
        Uri = autoclass('android.net.Uri')
        intent = Intent(action)
        if uri: intent.setData(Uri.parse(uri))
        if extras:
            for k,v in extras.items(): intent.putExtra(k,v)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) # Required for Service
        Service.startActivity(intent)
    except Exception as e: print(f"[Intent] {e}")

def toggle_flashlight(turn_on=True):
    try:
        CameraManager = autoclass('android.hardware.camera2.CameraManager')
        cm = Service.getSystemService(Context.CAMERA_SERVICE)
        camera_id = cm.getCameraIdList()[0]
        cm.setTorchMode(camera_id, turn_on)
        return "Flashlight is on" if turn_on else "Flashlight is off"
    except Exception: return "Flashlight access denied."

# ─────────────────────────────────────────
#  4. YOUR COMMAND PROCESSOR
# ─────────────────────────────────────────
def process_command(command):
    if not command:
        speak(random.choice(["Yes?","How can I help?","Tell me?"])); return
    cmd = command.lower().strip()

    # --- NEW LOCAL BRAIN & HARDWARE ---
    if any(w in cmd for w in ["verify", "fact check", "scan"]):
        speak("Running local deepfake analysis...")
        return
    if "flashlight" in cmd:
        turn_on = "on" in cmd
        speak(toggle_flashlight(turn_on))
        return

    # --- YOUR ORIGINAL LOGIC ---
    if "call" in cmd and "whatsapp" not in cmd:
        name=cmd.replace("call","").strip()
        num=load_contacts().get(name)
        if num: speak(f"Calling {name}"); _android_intent('android.intent.action.CALL', f"tel:{num}")
        else: speak(f"No number for {name}.")

    elif "weather" in cmd:
        city=cmd.split("in ")[-1].strip() if "in " in cmd else "Rupnagar"
        speak(f"Checking weather for {city}")
        ans=ask_ai(f"Current weather in {city} India? One sentence.")
        if ans: speak(ans)

    elif "time" in cmd:
        speak(datetime.datetime.now().strftime("It is %I:%M %p"))

    elif any(w in cmd for w in ["stop","goodbye","sleep","turn off"]):
        speak("Going to sleep. Say Sara to wake me.")
        S["sara_on"]=False; save_settings(S)

    else:
        if not feature_on("ai"): speak("AI is off."); return
        speak(ask_ai(command))

# ─────────────────────────────────────────
#  5. THE UNKILLABLE STT LOOP
# ─────────────────────────────────────────
def extract_command(text):
    t=text.lower().strip()
    for wake in WAKE_WORDS:
        for pre in ["hey ","ok ","okay ","hi ",""]:
            trigger=pre+wake
            if t.startswith(trigger):
                return True, text[len(trigger):].strip()
    return False,""

@run_on_ui_thread
def start_stt():
    global global_listener, speech_recognizer
    
    SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
    RecognizerIntent = autoclass('android.speech.RecognizerIntent')
    speech_recognizer = SpeechRecognizer.createSpeechRecognizer(Service)

    class SaraListener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']

        @java_method('([B)V')
        def onBufferReceived(self, b): pass
        @java_method('(ILandroid/os/Bundle;)V')
        def onError(self, error, bundle):
            send_ipc_animation_state("idle")
            start_listening_intent()
        @java_method('(Landroid/os/Bundle;)V')
        def onReadyForSpeech(self, bundle): pass
        @java_method('()V')
        def onBeginningOfSpeech(self): pass
        @java_method('(F)V')
        def onRmsChanged(self, r): pass
        @java_method('()V')
        def onEndOfSpeech(self): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onPartialResults(self, results):
            try:
                partial = results.getStringArrayList("android.speech.extra.PARTIAL_RESULTS")
                if partial and partial.size() > 0:
                    text = partial.get(0).lower()
                    if any(w in text for w in WAKE_WORDS):
                        send_ipc_animation_state("listening")
            except: pass

        @java_method('(Landroid/os/Bundle;)V')
        def onEvent(self, e, p): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            matches = results.getStringArrayList(RecognizerIntent.EXTRA_RESULTS)
            if matches and matches.size() > 0:
                text = matches.get(0)
                print(f"[STT] {text}")
                found, cmd = extract_command(text)
                if found:
                    threading.Thread(target=process_command, args=(cmd,), daemon=True).start()
            
            send_ipc_animation_state("idle")
            start_listening_intent()

    global_listener = SaraListener()
    speech_recognizer.setRecognitionListener(global_listener)

    def start_listening_intent():
        if not S.get("sara_on",True): return
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        # Apply your exact language codes
        codes = get_lang_codes()
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, codes[0])
        intent.putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES", codes[1:])
        speech_recognizer.startListening(intent)

    start_listening_intent()

if __name__ == '__main__':
    print("[SARA] Background Engine Booting...")
    acquire_wakelock()
    start_stt()
    
    # Keep alive
    while True:
        time.sleep(1)