# ═══════════════════════════════════════════════════════════════
#  S.A.R.A — Smart Assistant with Real-time Audio
#  NO UI — runs completely in background like Siri
#  Auto-starts on phone boot
#  Uses Android built-in speech engine (best accuracy)
#  All Indian accents: en-IN, hi-IN, pa-IN + more
# ═══════════════════════════════════════════════════════════════

import os, json, re, time, random, datetime, threading, requests

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
CONTACTS_FILE = os.path.join(BASE_DIR, "contacts.json")
CACHE_FILE    = os.path.join(BASE_DIR, "cache.json")

GROQ_API_KEY   = "YOUR_GROQ_API_KEY"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

DEFAULT_SETTINGS = {
    "language":"en","emotion":"friendly","sara_on":True,
    "features":{"sms":True,"whatsapp":True,"calls":True,
                "weather":True,"ai":True},
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
#  WAKE WORDS — Sara + all variations
# ─────────────────────────────────────────
WAKE_WORDS = [
    "sara","sarah","saara","sarra",
    "hey sara","ok sara","okay sara","hi sara",
    "hey sarah","ok sarah",
    "\u0938\u093e\u0930\u093e",
    "\u0a38\u0a3e\u0a30\u0a3e",
    "zara","tara","siri","zero","sar",
    "sara ji","sarah ji",
]

# All Indian + global accent codes
LANG_CODES = {
    "en": ["en-IN","en-US","en-GB","en-AU"],
    "hi": ["hi-IN","en-IN"],
    "pa": ["pa-IN","hi-IN","en-IN"],
}

def get_lang_codes():
    return LANG_CODES.get(S.get("language","en"), LANG_CODES["en"])

# ─────────────────────────────────────────
#  SPEAK
# ─────────────────────────────────────────
def speak(text):
    print(f"[Sara] {text}")
    try:
        from plyer import tts
        tts.speak(text)
    except Exception as e:
        print(f"[TTS] {e}")

# ─────────────────────────────────────────
#  AUTO DETECT LANGUAGE + EMOTION
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
#  CACHE
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
#  AI BRAIN
# ─────────────────────────────────────────
SARA_SYSTEM = ("You are Sara, a smart voice assistant. "
               "Reply in 1-2 short sentences. No markdown. Plain spoken language.")

def ask_ai(prompt):
    cached = cache_get(f"ai_{prompt[:40]}")
    if cached: return cached
    for key,url,body in [
        (GROQ_API_KEY,
         "https://api.groq.com/openai/v1/chat/completions",
         {"model":"llama3-8b-8192",
          "messages":[{"role":"system","content":SARA_SYSTEM},
                      {"role":"user","content":prompt}],
          "max_tokens":120}),
        (GEMINI_API_KEY,
         f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
         {"contents":[{"parts":[{"text":prompt}]}],
          "generationConfig":{"maxOutputTokens":120}}),
    ]:
        try:
            headers = {"Content-Type":"application/json"}
            if "groq" in url: headers["Authorization"] = f"Bearer {key}"
            resp = requests.post(url,headers=headers,json=body,timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ans = (data["choices"][0]["message"]["content"].strip()
                       if "groq" in url else
                       data["candidates"][0]["content"]["parts"][0]["text"].strip())
                cache_set(f"ai_{prompt[:40]}", ans)
                return ans
        except Exception as e:
            print(f"[AI] {e}")
    return "Sorry, I could not reach the internet right now."

# ─────────────────────────────────────────
#  ANDROID ACTIONS
# ─────────────────────────────────────────
def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE) as f: return json.load(f)
    s={"mom":"+919XXXXXXXXX","dad":"+919XXXXXXXXX","friend":"+919XXXXXXXXX"}
    json.dump(s,open(CONTACTS_FILE,"w"),indent=2); return s

def _android_intent(action, uri=None, extras=None):
    try:
        from jnius import autoclass
        Intent = autoclass('android.content.Intent')
        Uri    = autoclass('android.net.Uri')
        PA     = autoclass('org.kivy.android.PythonActivity')
        intent = Intent(action)
        if uri: intent.setData(Uri.parse(uri))
        if extras:
            for k,v in extras.items(): intent.putExtra(k,v)
        PA.mActivity.startActivity(intent)
    except Exception as e: print(f"[Intent] {e}")

def make_call(number):
    _android_intent('android.intent.action.CALL', f"tel:{number}")

def send_sms(number, msg):
    _android_intent('android.intent.action.SENDTO',
                    f"smsto:{number}", {"sms_body":msg})

def send_whatsapp(number, msg):
    try:
        import webbrowser
        webbrowser.open(f"whatsapp://send?phone={number}&text={msg.replace(' ','%20')}")
    except Exception as e: print(f"[WA] {e}")

def open_url(target):
    try:
        import webbrowser
        urls={"youtube":"https://youtube.com","google":"https://google.com",
              "whatsapp":"https://web.whatsapp.com","instagram":"https://instagram.com",
              "facebook":"https://facebook.com","twitter":"https://twitter.com"}
        webbrowser.open(urls.get(target.lower(),
            f"https://google.com/search?q={target.replace(' ','+')}"))
    except: pass

def get_battery():
    try:
        from plyer import battery
        s=battery.status; pct=int(s.get("percentage",0))
        state="charging" if s.get("isCharging") else "not charging"
        speak(f"Battery is at {pct} percent and {state}.")
        return pct,s.get("isCharging",False)
    except: return 0,False

_bf=False; _bl=False
def battery_monitor():
    global _bf,_bl
    while True:
        try:
            pct,plug=get_battery()
            if pct>=100 and plug and not _bf and S["battery"]["full_alert"]:
                speak("Battery fully charged. You can unplug."); _bf=True
            if pct<=20 and not plug and not _bl and S["battery"]["low_alert"]:
                speak("Battery is low. Please charge."); _bl=True
            if not plug: _bf=False
            if plug:     _bl=False
        except: pass
        time.sleep(60)

# ─────────────────────────────────────────
#  COMMAND PROCESSOR
# ─────────────────────────────────────────
def process_command(command):
    if not command:
        speak(random.choice(["Yes?","How can I help?","Tell me?"])); return
    auto_detect(command)
    cmd = command.lower().strip()

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

    elif any(w in cmd for w in ["send sms","send message","text"]):
        if "to" in cmd and "saying" in cmd:
            to=cmd.split("to")[1].split("saying")[0].strip()
            msg=cmd.split("saying")[1].strip()
            num=load_contacts().get(to)
            if num: send_sms(num,msg); speak(f"SMS sent to {to}")
            else: speak(f"No number for {to}.")
        else: speak("Say: send SMS to mom saying your message")

    elif "whatsapp" in cmd and "saying" in cmd and "to" in cmd:
        to=cmd.split("to")[1].split("saying")[0].strip()
        msg=cmd.split("saying")[1].strip()
        num=load_contacts().get(to)
        if num: send_whatsapp(num,msg); speak(f"WhatsApp sent to {to}")
        else: speak(f"No number for {to}.")

    elif "weather" in cmd:
        city=cmd.split("in ")[-1].strip() if "in " in cmd else "Pathankot"
        cached=cache_get(f"weather_{city}")
        if cached: speak(cached)
        else:
            speak(f"Checking weather for {city}")
            ans=ask_ai(f"Current weather in {city} India? One sentence.")
            if ans: cache_set(f"weather_{city}",ans); speak(ans)

    elif "battery" in cmd: get_battery()

    elif "time" in cmd:
        speak(datetime.datetime.now().strftime("It is %I:%M %p"))

    elif "date" in cmd or "day" in cmd:
        speak(datetime.datetime.now().strftime("Today is %A, %B %d"))

    elif "open" in cmd:
        t=cmd.replace("open","").strip()
        open_url(t); speak(f"Opening {t}")

    elif any(w in cmd for w in ["stop","goodbye","sleep","turn off"]):
        speak("Going to sleep. Say Sara to wake me.")
        S["sara_on"]=False; save_settings(S)

    elif any(w in cmd for w in ["wake up","start","turn on"]):
        S["sara_on"]=True; save_settings(S)
        speak("I'm back! How can I help?")

    elif "help" in cmd or "what can you do" in cmd:
        speak("Say Sara then: call, SMS, WhatsApp, weather, battery, "
              "time, open YouTube, or ask me anything.")
    else:
        if not feature_on("ai"): speak("AI is off."); return
        speak(ask_ai(command))

# ─────────────────────────────────────────
#  ANDROID SPEECH RECOGNIZER — ALWAYS ON
# ─────────────────────────────────────────
def extract_command(text):
    t=text.lower().strip()
    for wake in WAKE_WORDS:
        for pre in ["hey ","ok ","okay ","hi ",""]:
            trigger=pre+wake
            if t.startswith(trigger):
                return True, text[len(trigger):].strip()
    return False,""

def start_continuous_stt():
    """
    Start Android SpeechRecognizer in continuous loop.
    Uses phone's built-in speech chip — very low battery.
    Supports all Indian accents automatically.
    """
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        from kivy.clock import Clock

        SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
        RecognizerIntent = autoclass('android.speech.RecognizerIntent')
        Intent           = autoclass('android.content.Intent')
        PythonActivity   = autoclass('org.kivy.android.PythonActivity')

        rec = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)

        class Listener(PythonJavaClass):
            __javainterfaces__ = ['android/speech/RecognitionListener']

            @java_method('([B)V')
            def onBufferReceived(self,b): pass
            @java_method('(ILandroid/os/Bundle;)V')
            def onError(self,e,p):
                Clock.schedule_once(lambda dt:restart(),1)
            @java_method('(Landroid/os/Bundle;)V')
            def onReadyForSpeech(self,p): pass
            @java_method('(Landroid/os/Bundle;)V')
            def onBeginningOfSpeech(self,p): pass
            @java_method('(F)V')
            def onRmsChanged(self,r): pass
            @java_method('()V')
            def onEndOfSpeech(self): pass
            @java_method('(Landroid/os/Bundle;)V')
            def onPartialResults(self,p):
                try:
                    partial=p.getStringArrayList("android.speech.extra.PARTIAL_RESULTS")
                    if partial and partial.size()>0:
                        t=partial.get(0).lower()
                        if any(w in t for w in WAKE_WORDS):
                            print(f"[Partial wake] {t}")
                except: pass
            @java_method('(Landroid/os/Bundle;)V')
            def onResults(self,results):
                matches=results.getStringArrayList(RecognizerIntent.EXTRA_RESULTS)
                if matches and matches.size()>0:
                    text=matches.get(0)
                    print(f"[STT] {text}")
                    found,cmd=extract_command(text)
                    if found:
                        threading.Thread(target=process_command,
                                        args=(cmd,),daemon=True).start()
                if S.get("sara_on",True):
                    Clock.schedule_once(lambda dt:restart(),0.3)
            @java_method('(ILandroid/os/Bundle;)V')
            def onEvent(self,e,p): pass

        listener=Listener()
        rec.setRecognitionListener(listener)

        def restart():
            if not S.get("sara_on",True): return
            try:
                codes=get_lang_codes()
                intent=Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, codes[0])
                intent.putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES",
                                codes[1:])
                intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
                intent.putExtra(
                    RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
                    1500)
                rec.startListening(intent)
            except Exception as e:
                print(f"[STT restart] {e}")
                Clock.schedule_once(lambda dt:restart(),2)

        restart()
        print("[Sara] STT started — say 'Sara' to activate")

    except Exception as e:
        print(f"[STT] Not in APK: {e}")

# ─────────────────────────────────────────
#  SCREEN ON/OFF + WAKELOCK
# ─────────────────────────────────────────
_screen_on=True
_wakelock=None

def acquire_wakelock():
    global _wakelock
    try:
        from jnius import autoclass
        PM=autoclass('android.os.PowerManager')
        PA=autoclass('org.kivy.android.PythonActivity')
        pm=PA.mActivity.getSystemService(PA.mActivity.POWER_SERVICE)
        _wakelock=pm.newWakeLock(PM.PARTIAL_WAKE_LOCK,'Sara:WakeLock')
        _wakelock.acquire()
    except Exception as e: print(f"[WakeLock] {e}")

def setup_screen_monitor():
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        from kivy.clock import Clock
        Intent=autoclass('android.content.Intent')
        IntentFilter=autoclass('android.content.IntentFilter')
        PA=autoclass('org.kivy.android.PythonActivity')

        class ScreenReceiver(PythonJavaClass):
            __javainterfaces__=['android/content/BroadcastReceiver']
            @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
            def onReceive(self,ctx,intent):
                global _screen_on
                action=intent.getAction()
                if action==Intent.ACTION_SCREEN_OFF:
                    _screen_on=False
                    print("[Screen] OFF — pausing STT")
                elif action==Intent.ACTION_SCREEN_ON:
                    _screen_on=True
                    acquire_wakelock()
                    print("[Screen] ON — resuming STT")
                    if S.get("sara_on",True):
                        Clock.schedule_once(
                            lambda dt:start_continuous_stt(),0.5)

        f=IntentFilter()
        f.addAction(Intent.ACTION_SCREEN_ON)
        f.addAction(Intent.ACTION_SCREEN_OFF)
        f.addAction("android.intent.action.USER_PRESENT")
        PA.mActivity.registerReceiver(ScreenReceiver(),f)
    except Exception as e: print(f"[Screen monitor] {e}")

# ─────────────────────────────────────────
#  FOREGROUND NOTIFICATION
# ─────────────────────────────────────────
def start_foreground():
    try:
        from jnius import autoclass
        PA=autoclass('org.kivy.android.PythonActivity')
        NB=autoclass('android.app.Notification$Builder')
        NM=autoclass('android.app.NotificationManager')
        NC=autoclass('android.app.NotificationChannel')
        ctx=PA.mActivity
        ch=NC("sara","Sara Assistant",NM.IMPORTANCE_LOW)
        ctx.getSystemService(ctx.NOTIFICATION_SERVICE).createNotificationChannel(ch)
        n=NB(ctx,"sara")\
            .setContentTitle("Sara is listening")\
            .setContentText("Say 'Sara' to activate")\
            .setSmallIcon(17301543)\
            .setOngoing(True)\
            .build()
        ctx.startForeground(1,n)
        print("[Foreground] Service started")
    except Exception as e: print(f"[Foreground] {e}")

# ─────────────────────────────────────────
#  KIVY APP — NO UI
# ─────────────────────────────────────────
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window

class SaraApp(App):
    def build(self):
        Window.size=(1,1)   # invisible window
        try: Window.hide()
        except: pass
        return Widget()     # no UI

    def on_start(self):
        threading.Thread(target=start_foreground,daemon=True).start()
        threading.Thread(target=battery_monitor,daemon=True).start()
        self._request_permissions()
        acquire_wakelock()
        setup_screen_monitor()
        threading.Thread(target=start_continuous_stt,daemon=True).start()
        h=datetime.datetime.now().hour
        g="Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening"
        speak(f"{g}! Sara is ready. Say Sara to activate.")

    def _request_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.RECORD_AUDIO,
                Permission.SEND_SMS,
                Permission.CALL_PHONE,
                Permission.READ_CONTACTS,
                Permission.WRITE_CONTACTS,
                Permission.READ_PHONE_STATE,
                Permission.INTERNET,
                Permission.RECEIVE_BOOT_COMPLETED,
                Permission.FOREGROUND_SERVICE,
            ])
        except Exception as e: print(f"[Perms] {e}")

    def on_pause(self): return True
    def on_resume(self): pass

if __name__ == "__main__":
    SaraApp().run()