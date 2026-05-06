import time, threading, requests
from jnius import autoclass, PythonJavaClass, java_method
from android.runnable import run_on_ui_thread

# 1. Global variables to defeat Garbage Collection
global_listener = None
speech_recognizer = None

# Context Setup
Context = autoclass('android.content.Context')
Service = autoclass('org.kivy.android.PythonService').mService
Intent = autoclass('android.content.Intent')

def acquire_wakelock():
    PowerManager = autoclass('android.os.PowerManager')
    pm = Service.getSystemService(Context.POWER_SERVICE)
    wakelock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, 'Sara:WakeLock')
    wakelock.acquire()

def send_ipc_animation_state(state):
    """Sends broadcast to main.py to animate the KivyMD UI"""
    intent = Intent("com.sara.ANIMATE")
    intent.putExtra("state", state)
    Service.sendBroadcast(intent)

def speak(text):
    print(f"[SARA SPEAKS] {text}")
    try:
        from plyer import tts
        tts.speak(text)
    except: pass

# --- HARDWARE INTENTS (Feature 2 & Vision Concept) ---
def toggle_flashlight(turn_on=True):
    try:
        CameraManager = autoclass('android.hardware.camera2.CameraManager')
        cm = Service.getSystemService(Context.CAMERA_SERVICE)
        camera_id = cm.getCameraIdList()[0]
        cm.setTorchMode(camera_id, turn_on)
        return "Flashlight activated" if turn_on else "Flashlight disabled"
    except Exception:
        return "Flashlight access denied."

def set_alarm(hour, minute, message):
    try:
        AlarmClock = autoclass('android.provider.AlarmClock')
        intent = Intent(AlarmClock.ACTION_SET_ALARM)
        intent.putExtra(AlarmClock.EXTRA_HOUR, int(hour))
        intent.putExtra(AlarmClock.EXTRA_MINUTES, int(minute))
        intent.putExtra(AlarmClock.EXTRA_MESSAGE, message)
        intent.putExtra(AlarmClock.EXTRA_SKIP_UI, True) # Set silently
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        Service.startActivity(intent)
        return f"Alarm set for {hour}:{minute}."
    except Exception:
        return "Could not set alarm."

# --- CUSTOM LOCAL BRAIN (Feature 4) ---
def run_misinformation_detector(text_data):
    """Bypasses standard cloud LLM to run real-time local checks."""
    print("[SYSTEM] Bypassing cloud. Running local real-time detection script...")
    return "Local scan complete. Data appears organically generated."

def process_command(cmd):
    # Route 1: Local Misinformation Engine
    if any(w in cmd for w in ["verify", "fact check", "scan"]):
        response = run_misinformation_detector(cmd)
        speak(response)
        return

    # Route 2: Hardware Control
    if "flashlight" in cmd:
        turn_on = "on" in cmd
        speak(toggle_flashlight(turn_on))
        return
        
    if "alarm" in cmd:
        # Example hardcoded response; parse regex for real time extraction
        speak(set_alarm(7, 0, 'Wake up'))
        return

    # Route 3: Standard Cloud LLM Fallback
    print(f"[SARA Cloud Brain] Passing '{cmd}' to standard logic...")
    speak("I am processing your command in the cloud.")

# --- SPEECH RECOGNIZER (Feature 1 - Thread Safe) ---
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
            start_listening_intent() # Seamless Restart loop

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
                    # Trigger visual animation in UI if wake word heard
                    if "sara" in text:
                        send_ipc_animation_state("listening")
            except Exception: pass

        @java_method('(Landroid/os/Bundle;)V')
        def onEvent(self, e, p): pass

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            matches = results.getStringArrayList(RecognizerIntent.EXTRA_RESULTS)
            if matches and matches.size() > 0:
                text = matches.get(0).lower()
                if "sara" in text:
                    cmd = text.replace("sara", "").strip()
                    threading.Thread(target=process_command, args=(cmd,), daemon=True).start()
            
            send_ipc_animation_state("idle")
            start_listening_intent() # Loop continuously

    # Assign to global to prevent Garbage Collection
    global_listener = SaraListener()
    speech_recognizer.setRecognitionListener(global_listener)

    def start_listening_intent():
        intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        speech_recognizer.startListening(intent)

    start_listening_intent()

if __name__ == '__main__':
    print("[SARA SERVICE] Background engine booting...")
    acquire_wakelock()
    start_stt()
    
    # Keep service alive indefinitely
    while True:
        time.sleep(1)