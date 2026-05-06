import os, json, time, random, datetime, threading, requests
from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

# --- 1. ANDROID GLOBALS & WAKELOCK ---
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
    except Exception as e: print(f"[WakeLock] {e}")

def send_ipc_animation_state(state):
    try:
        intent = Intent("com.sara.ANIMATE")
        intent.putExtra("state", state)
        Service.sendBroadcast(intent)
    except: pass

# --- 2. YOUR ORIGINAL CONFIG & SETTINGS ---
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

# --- EMOTION DETECTOR ---
HINDI_W   = ["kya","hai","karo","bolo","batao","mujhe","haan","nahi"]
PUNJABI_W = ["ki","hega","dasso","oye","tusi","menu","sada","eh"]
EMOTIONS  = {
    "happy":["happy","great","awesome","excited","wonderful"],
    "sad":["sad","upset","crying","unhappy","lonely"],
    "angry":["angry","frustrated","hate","worst","mad"],
    "stressed":["busy","tired","exhausted","stressed","urgent"],
    "calm":["okay","fine","alright","sure","thanks"],
}
EMO_TO_STYLE = {"happy":"friendly","sad":"caring","angry":"calm",
                "stressed":"calm","calm":"friendly"}

def auto_detect(text):
    if any('\u0900'<=c<='\u097f' for c in text): lang="hi"
    elif any('\u0a00'<=c<='\u0a7f' for c in text): lang="pa"
    else:
        t=text.lower(); w=t.split()
        lang = "pa" if sum(1 for x in w if x in PUNJABI_W)>=2 else \
               "hi" if sum(1 for x in w if x in HINDI_W)>=2 else "en"
    if lang != S.get("language","en"): S["language"]=lang; save_settings(S)
    t=text.lower()
    scores={e:sum(1 for w in EMOTIONS[e] if w in t) for e in EMOTIONS}
    best=max(scores,key=scores.get)
    emo=EMO_TO_STYLE.get(best if scores[best]>0 else "calm","friendly")
    if emo != S.get("emotion","friendly"): S["emotion"]=emo; save_settings(S)

def cache_get(key):
    try:
        data = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
        e = data.get(key)
        if e and time.time()-e.get("ts",0)<7*86400: return e.get("value")
    except: pass
    return None

def cache_set(key,value):
    try:
        data = json.load(open(CACHE_FILE)) if os.path.exists(CACHE_FILE) else {}
        data[key]={"value":value,"ts":time.time()}
        json.dump(data,open(CACHE_FILE,"w"),indent=2)
    except: pass

# --- AI BRAIN ---
SARA_SYSTEM = ("You are Sara, a smart voice assistant with emotions. WHo can tallk to the user in a friendly, caring, or calm style based on their mood that wiil the user tlk in. Reply in 1-2 short sentences. No markdown. Plain spoken language. and reply in their language which they used to talk to you.")

def ask_ai(prompt):
    cached = cache_get(f"ai_{prompt[:40]}")
    if cached: return cached
    for key,url,body in [
        (GROQ_API_KEY, "https://api.groq.com/openai/v1/chat/completions",
         {"model":"llama3-8b-8192", "messages":[{"role":"system","content":SARA_SYSTEM}, {"role":"user","content":prompt}], "max_tokens":120}),
        (GEMINI_API_KEY, f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
         {"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"maxOutputTokens":120}}),
    ]:
        try:
            headers = {"Content-Type":"application/json"}
            if "groq" in url: headers["Authorization"] = f"Bearer {key}"
            resp = requests.post(url,headers=headers,json=body,timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ans = (data["choices"][0]["message"]["content"].strip() if "groq" in url else data["candidates"][0]["content"]["parts"][0]["text"].strip())
                cache_set(f"ai_{prompt[:40]}", ans)
                return ans
        except Exception as e: print(f"[AI Error] {e}")
    return "Sorry, I could not reach the internet right now."

# --- 3. BACKGROUND-SAFE ANDROID ACTIONS ---
def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE) as f: return json.load(f)
    s={"mom":"+919XXXXXXXXX","dad":"+919XXXXXXXXX","friend":"+919XXXXXXXXX"}
    json.dump(s,open(CONTACTS_FILE,"w"),indent=2); return s

def _android_intent(action, uri=None, extras=None):
    try:
        Uri = autoclass('android.net.Uri')
        intent = Intent(action)
        if uri: intent.setData(Uri.parse(uri))
        if extras:
            for k,v in extras.items(): intent.putExtra(k,v)
        # CRITICAL for background services opening apps
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) 
        Service.startActivity(intent)
    except Exception as e: print(f"[Intent] {e}")

def make_call(number): _android_intent('android.intent.action.CALL', f"tel:{number}")
def send_sms(number, msg): _android_intent('android.intent.action.SENDTO', f"smsto:{number}", {"sms_body":msg})

def send_whatsapp(number, msg):
    url = f"https://api.whatsapp.com/send?phone={number}&text={msg.replace(' ','%20')}"
    _android_intent(Intent.ACTION_VIEW, uri=url)

def open_url(target):
    urls={"youtube":"https://youtube.com","google":"https://google.com","whatsapp":"https://web.whatsapp.com"}
    url = urls.get(target.lower(), f"https://google.com/search?q={target.replace(' ','+')}")
    _android_intent(Intent.ACTION_VIEW, uri=url)

# --- HARDWARE & BATTERY ---
def toggle_flashlight(turn_on=True):
    try:
        CameraManager = autoclass('android.hardware.camera2.CameraManager')
        cm = Service.getSystemService(Context.CAMERA_SERVICE)
        cm.setTorchMode(cm.getCameraIdList()[0], turn_on)
        return "Flashlight activated" if turn_on else "Flashlight disabled"
    except: return "Flashlight access denied."

_bf=False; _bl=False
def battery_monitor():
    global _bf,_bl
    while True:
        try:
            from plyer import battery
            s = battery.status; pct = int(s.get("percentage",0))
            plug = s.get("isCharging", False)
            if pct>=100 and plug and not _bf and S["battery"]["full_alert"]:
                speak("Battery fully charged. You can unplug."); _bf=True
            if pct<=20 and not plug and not _bl and S["battery"]["low_alert"]:
                speak("Battery is low. Please charge."); _bl=True
            if not plug: _bf=False
            if plug: _bl=False
        except: pass
        time.sleep(60)

# --- 4. THE COMMAND PROCESSOR ---
def process_command(command):
    if not command:
        speak(random.choice(["Yes?","How can I help?","Tell me?"])); return
    auto_detect(command)
    cmd = command.lower().strip()

    if any(w in cmd for w in ["verify", "fact check", "scan"]):
        speak("Running local deepfake analysis...")
        return
    if "flashlight" in cmd:
        turn_on = "on" in cmd
        speak(toggle_flashlight(turn_on))
        return

    if "call" in cmd and "whatsapp" not in cmd:
        name=cmd.replace("call","").strip()
        num=load_contacts().get(name)
        if num: speak(f"Calling {name}"); make_call(num)
        else: speak(f"No number for {name}.")

    elif "whatsapp" in cmd and "call" in cmd:
        name=cmd.replace("whatsapp","").replace("call","").strip()
        num=load_contacts().get(name)
        if num: send_whatsapp(num,""); speak(f"Opening WhatsApp for {name}")
        else: speak(f"No number for {name}.")

    elif "whatsapp" in cmd and "saying" in cmd and "to" in cmd:
        to=cmd.split("to")[1].split("saying")[0].strip()
        msg=cmd.split("saying")[1].strip()
        num=load_contacts().get(to)
        if num: send_whatsapp(num,msg); speak(f"WhatsApp sent to {to}")
        else: speak(f"No number for {to}.")

    elif any(w in cmd for w in ["send sms","send message","text"]):
        if "to" in cmd and "saying" in cmd:
            to=cmd.split("to")[1].split("saying")[0].strip()
            msg=cmd.split("saying")[1].strip()
            num=load_contacts().get(to)
            if num: send_sms(num,msg); speak(f"SMS sent to {to}")
            else: speak(f"No number for {to}.")

    elif "weather" in cmd:
        city=cmd.split("in ")[-1].strip() if "in " in cmd else "Rupnagar"
        ans=ask_ai(f"Current weather in {city} India? One sentence.")
        if ans: speak(ans)

    elif "time" in cmd: speak(datetime.datetime.now().strftime("It is %I:%M %p"))
    elif "date" in cmd or "day" in cmd: speak(datetime.datetime.now().strftime("Today is %A, %B %d"))

    elif "open" in cmd:
        t=cmd.replace("open","").strip()
        open_url(t); speak(f"Opening {t}")

    elif any(w in cmd for w in ["stop","goodbye","sleep","turn off"]):
        speak("Going to sleep. Say Sara to wake me.")
        S["sara_on"]=False; save_settings(S)

    elif any(w in cmd for w in ["wake up","start","turn on"]):
        S["sara_on"]=True; save_settings(S)
        speak("I'm back! How can I help?")

    else:
        if not feature_on("ai"): speak("AI is off."); return
        speak(ask_ai(command))

# --- 5. THE UNKILLABLE STT LOOP ---
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
        codes = get_lang_codes()
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, codes[0])
        intent.putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES", codes[1:])
        speech_recognizer.startListening(intent)

    start_listening_intent()

# --- 6. FOREGROUND NOTIFICATION (Required by Android) ---
def start_foreground():
    try:
        Context = autoclass('android.content.Context')
        Service = autoclass('org.kivy.android.PythonService').mService
        NB = autoclass('android.app.Notification$Builder')
        NM = autoclass('android.app.NotificationManager')
        NC = autoclass('android.app.NotificationChannel')

        # Create Notification Channel
        channel_id = "sara_bg"
        ch = NC(channel_id, "S.A.R.A Background", NM.IMPORTANCE_LOW)
        manager = Service.getSystemService(Context.NOTIFICATION_SERVICE)
        manager.createNotificationChannel(ch)

        # Get the app's default icon
        app_info = Service.getApplicationInfo()
        icon = app_info.icon

        # Build the permanent notification
        n = NB(Service, channel_id)\
            .setContentTitle("S.A.R.A is Active")\
            .setContentText("Listening for commands...")\
            .setSmallIcon(icon)\
            .setOngoing(True)\
            .build()

        # Start Foreground to prevent Android from killing the app
        Service.startForeground(1, n)
        print("[Foreground] Persistent Notification Started!")
    except Exception as e: 
        print(f"[Foreground] Error: {e}")

if __name__ == '__main__':
    print("[SARA] Background Engine Booting...")
    
    # 1. Start the notification FIRST so Android doesn't kill us!
    start_foreground() 
    
    # 2. Get WakeLock and start systems
    acquire_wakelock()
    threading.Thread(target=battery_monitor, daemon=True).start()
    start_stt()
    
    # Keep alive
    while True: time.sleep(1)
        
