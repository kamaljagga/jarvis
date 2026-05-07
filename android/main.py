# ═══════════════════════════════════════════════════════════════
#  S.A.R.A — main.py (KivyMD UI + Service Launcher)
#  Fixes vs original:
#  ✅ IPCReceiver stored as self.receiver (prevents GC)
#  ✅ Correct IPC action: com.yourname.sara.ANIMATE
#  ✅ Correct ServiceSara class name from buildozer
#  ✅ Siri-style orb animation using KivyMD + Canvas
#  ✅ Permission callback handles each permission individually
#  ✅ Notification permission handled for Android 13+
# ═══════════════════════════════════════════════════════════════

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.utils import get_color_from_hex

from jnius import autoclass, PythonJavaClass, java_method
from android.permissions import request_permissions, Permission, check_permission

# ─────────────────────────────────────────
#  SIRI-STYLE ORB WIDGET
#  Animated circle that pulses when listening
# ─────────────────────────────────────────
class SaraOrb(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._anim      = None
        self._color     = [0.2, 0.6, 1.0, 1.0]   # idle blue
        self._radius    = 80
        self._draw()
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self._color)
            cx = self.center_x - self._radius
            cy = self.center_y - self._radius
            d  = self._radius * 2
            Ellipse(pos=(cx, cy), size=(d, d))
            # Outer glow ring
            Color(self._color[0], self._color[1], self._color[2], 0.15)
            gr = self._radius + 20
            Ellipse(pos=(self.center_x - gr, self.center_y - gr),
                    size=(gr*2, gr*2))

    def set_idle(self):
        """Blue — waiting for wake word."""
        if self._anim: self._anim.stop(self); self._anim = None
        self._color = [0.2, 0.6, 1.0, 1.0]
        self._radius = 80
        self._draw()

    def set_listening(self):
        """Red pulsing orb — wake word detected, listening for command."""
        def _update_anim(val):
            self._radius = val
            self._draw()

        self._color = [1.0, 0.2, 0.2, 1.0]
        self._draw()

        # Pulse animation: 80 → 100 → 80
        from kivy.animation import Animation
        self._anim = Animation(duration=0.4) + Animation(duration=0.4)
        # Use a proxy float for animation
        self._pulse_val = 80.0
        anim = (Animation(_pulse_val=100, duration=0.35) +
                Animation(_pulse_val=80,  duration=0.35))
        anim.repeat = True
        anim.bind(on_progress=lambda *a: _update_anim(self._pulse_val))
        anim.start(self)
        self._anim = anim

    def set_processing(self):
        """Purple — processing command."""
        if self._anim: self._anim.stop(self); self._anim = None
        self._color = [0.6, 0.2, 1.0, 1.0]
        self._radius = 80
        self._draw()

    def set_speaking(self):
        """Green — Sara is speaking."""
        if self._anim: self._anim.stop(self); self._anim = None
        self._color = [0.1, 0.8, 0.4, 1.0]
        self._radius = 90
        self._draw()


# ─────────────────────────────────────────
#  IPC BROADCAST RECEIVER
#  Receives state from service.py
#  Updates UI animation accordingly
# ─────────────────────────────────────────
class IPCReceiver(PythonJavaClass):
    __javainterfaces__ = ['android/content/BroadcastReceiver']

    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
    def onReceive(self, context, intent):
        action = intent.getAction()
        if action == "com.yourname.sara.ANIMATE":
            state = intent.getStringExtra("state")
            # MUST update UI on main thread
            Clock.schedule_once(lambda dt: self.callback(state), 0)


# ─────────────────────────────────────────
#  MAIN SCREEN
# ─────────────────────────────────────────
class SaraScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = [0.04, 0.04, 0.08, 1]

        # Orb
        self.orb = SaraOrb(
            size_hint=(None, None),
            size=(dp(200), dp(200)),
            pos_hint={"center_x": 0.5, "center_y": 0.58}
        )
        self.add_widget(self.orb)

        # Name label
        name_lbl = MDLabel(
            text="S.A.R.A",
            pos_hint={"center_x": 0.5, "center_y": 0.82},
            halign="center",
            font_style="H4",
            theme_text_color="Custom",
            text_color=[0.9, 0.9, 0.9, 1]
        )
        self.add_widget(name_lbl)

        subtitle = MDLabel(
            text="Smart Assistant with Real-time Audio",
            pos_hint={"center_x": 0.5, "center_y": 0.76},
            halign="center",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=[0.5, 0.5, 0.6, 1]
        )
        self.add_widget(subtitle)

        # Status label
        self.status = MDLabel(
            text="Initializing...",
            pos_hint={"center_x": 0.5, "center_y": 0.32},
            halign="center",
            font_style="Body1",
            theme_text_color="Custom",
            text_color=[0.7, 0.7, 0.8, 1]
        )
        self.add_widget(self.status)

        # State label (Idle / Listening / Processing)
        self.state_lbl = MDLabel(
            text="● Idle",
            pos_hint={"center_x": 0.5, "center_y": 0.25},
            halign="center",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=[0.2, 0.6, 1.0, 1]
        )
        self.add_widget(self.state_lbl)

        # Hint
        hint = MDLabel(
            text='Say "Sara" to activate',
            pos_hint={"center_x": 0.5, "center_y": 0.18},
            halign="center",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=[0.35, 0.35, 0.45, 1]
        )
        self.add_widget(hint)

    def trigger_animation(self, state):
        """Called by IPCReceiver when service sends a state update."""
        if state == "listening":
            self.orb.set_listening()
            self.state_lbl.text  = "● Listening..."
            self.state_lbl.text_color = [1.0, 0.3, 0.3, 1]
            self.status.text = "Wake word detected!"

        elif state == "processing":
            self.orb.set_processing()
            self.state_lbl.text  = "● Processing..."
            self.state_lbl.text_color = [0.6, 0.2, 1.0, 1]
            self.status.text = "Thinking..."

        elif state == "speaking":
            self.orb.set_speaking()
            self.state_lbl.text  = "● Speaking"
            self.state_lbl.text_color = [0.1, 0.8, 0.4, 1]
            self.status.text = "Sara is responding"

        else:   # idle
            self.orb.set_idle()
            self.state_lbl.text  = "● Idle"
            self.state_lbl.text_color = [0.2, 0.6, 1.0, 1]
            self.status.text = "Background Engine Running"


# ─────────────────────────────────────────
#  APP
# ─────────────────────────────────────────
class SaraApp(MDApp):
    def build(self):
        self.theme_cls.theme_style  = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.screen   = SaraScreen()
        self.receiver = None   # kept alive to prevent GC
        return self.screen

    def on_start(self):
        self.screen.status.text = "Requesting Permissions..."
        # Request all permissions upfront
        perms = [
            Permission.RECORD_AUDIO,
            Permission.CAMERA,
            Permission.CALL_PHONE,
            Permission.READ_CONTACTS,
            Permission.SEND_SMS,
            Permission.BLUETOOTH_CONNECT,
        ]
        # POST_NOTIFICATIONS required on Android 13+
        # Not in older Permission enum — use raw string
        try:
            perms.append(Permission.POST_NOTIFICATIONS)
        except AttributeError:
            perms.append('android.permission.POST_NOTIFICATIONS')

        request_permissions(perms, self.on_permissions_result)
        self._setup_ipc()

    def on_permissions_result(self, permissions, results):
        """Handle permission results individually."""
        granted = []
        denied  = []
        for perm, result in zip(permissions, results):
            (granted if result else denied).append(perm)

        if denied:
            missing = ", ".join(str(p).split(".")[-1] for p in denied)
            self.screen.status.text = f"Denied: {missing}. Some features limited."
        else:
            self.screen.status.text = "All permissions granted ✅"

        # Start service regardless — core features work without camera/BT
        if check_permission(Permission.RECORD_AUDIO):
            Clock.schedule_once(self._start_sara_service, 1.0)
        else:
            self.screen.status.text = "Microphone permission required!"

    def _start_sara_service(self, dt):
        """Start the background Sara service (foreground service with microphone)."""
        try:
            PA     = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')

            # Buildozer generates service class as:
            # {package.domain}.{package.name}.Service{ServiceName}
            # services = sara:service.py → ServiceSara
            ServiceClass = autoclass('com.yourname.sara.ServiceSara')

            mActivity = PA.mActivity
            intent    = Intent(mActivity, ServiceClass)
            intent.putExtra("pythonServiceArgument", "")
            mActivity.startForegroundService(intent)

            self.screen.status.text  = "Sara is running in background"
            self.screen.state_lbl.text = "● Active"
            print("[Main] ✅ Sara service started")

        except Exception as e:
            self.screen.status.text = f"Service Error: {e}"
            print(f"[Main] Service start error: {e}")

    def _setup_ipc(self):
        """Register BroadcastReceiver to get state updates from service."""
        try:
            IntentFilter = autoclass('android.content.IntentFilter')
            PA           = autoclass('org.kivy.android.PythonActivity')

            # ✅ Store in self.receiver — prevents GC while Java holds reference
            self.receiver = IPCReceiver(self.screen.trigger_animation)
            filt = IntentFilter("com.yourname.sara.ANIMATE")
            PA.mActivity.registerReceiver(self.receiver, filt)
            print("[IPC] ✅ BroadcastReceiver registered")
        except Exception as e:
            print(f"[IPC] Setup error: {e}")

    def on_pause(self):
        return True   # don't kill app when minimized

    def on_resume(self):
        pass

    def on_stop(self):
        # Unregister receiver cleanly
        try:
            if self.receiver:
                PA = autoclass('org.kivy.android.PythonActivity')
                PA.mActivity.unregisterReceiver(self.receiver)
        except: pass


if __name__ == "__main__":
    SaraApp().run()