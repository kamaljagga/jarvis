from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFloatingActionButton
from kivymd.uix.label import MDLabel
from kivy.animation import Animation
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method
from android.permissions import request_permissions, Permission

# --- IPC Receiver for Animations ---
class IPCReceiver(PythonJavaClass):
    __javainterfaces__ = ['android/content/BroadcastReceiver']
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
    def onReceive(self, context, intent):
        action = intent.getAction()
        if action == "com.sara.ANIMATE":
            state = intent.getStringExtra("state")
            Clock.schedule_once(lambda dt: self.callback(state))

class SaraUI(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.05, 0.05, 0.05, 1]

        self.mic_btn = MDFloatingActionButton(
            icon="microphone",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            md_bg_color=[0.2, 0.6, 1, 1],
            theme_icon_color="Custom",
            icon_color=[1, 1, 1, 1],
            elevation=2
        )
        self.add_widget(self.mic_btn)

        self.status = MDLabel(
            text="Initializing...",
            pos_hint={"center_x": 0.5, "center_y": 0.3},
            halign="center",
            theme_text_color="Custom",
            text_color=[0.8, 0.8, 0.8, 1]
        )
        self.add_widget(self.status)

    def trigger_animation(self, state):
        if state == "listening":
            self.status.text = "Listening..."
            anim = Animation(md_bg_color=[1, 0.2, 0.2, 1], duration=0.3) + \
                   Animation(md_bg_color=[0.8, 0.1, 0.1, 1], duration=0.3)
            anim.repeat = True
            anim.start(self.mic_btn)
        else:
            self.status.text = "S.A.R.A is active in background"
            Animation.cancel_all(self.mic_btn)
            anim = Animation(md_bg_color=[0.2, 0.6, 1, 1], duration=0.5)
            anim.start(self.mic_btn)

class SaraApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.ui = SaraUI()
        self.setup_ipc()
        return self.ui

    def on_start(self):
        self.ui.status.text = "Requesting Permissions..."
        request_permissions([
            Permission.RECORD_AUDIO, Permission.CAMERA,
            Permission.FOREGROUND_SERVICE, Permission.CALL_PHONE,
            Permission.READ_CONTACTS, Permission.SEND_SMS
        ], self.permissions_callback)

    def permissions_callback(self, permissions, results):
        if all(results):
            self.ui.status.text = "Permissions Granted. Starting Engine..."
            Clock.schedule_once(self.start_service, 1)
        else:
            self.ui.status.text = "Missing core permissions. Please restart."

    def start_service(self, dt):
        try:
            mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            Intent = autoclass('android.content.Intent')
            # Pointing exactly to the Service Buildozer generates
            ServiceClass = autoclass('com.yourname.sara.ServiceSara')
            
            intent = Intent(mActivity, ServiceClass)
            intent.putExtra("pythonServiceArgument", "")
            mActivity.startForegroundService(intent)
            
            self.ui.status.text = "Background Engine Running"
        except Exception as e:
            self.ui.status.text = f"Boot Error: {e}"
            print(f"Service Boot Error: {e}")

    def setup_ipc(self):
        try:
            IntentFilter = autoclass('android.content.IntentFilter')
            PA = autoclass('org.kivy.android.PythonActivity')
            self.receiver = IPCReceiver(self.ui.trigger_animation)
            PA.mActivity.registerReceiver(self.receiver, IntentFilter("com.sara.ANIMATE"))
        except: pass

if __name__ == "__main__":
    SaraApp().run()