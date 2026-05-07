[app]
title = Sara Assistant
package.name = sara
# CRITICAL: This must remain com.yourname to perfectly match main.py
package.domain = com.yourname

source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0

# Added kivymd, jnius, and required backend libraries
requirements = python3,kivy==2.3.0,kivymd,jnius,plyer,requests,android

orientation = portrait
fullscreen = 1

# Extensive permissions for hardware, vision, and background services
android.permissions = INTERNET, RECORD_AUDIO, CAMERA, SET_ALARM, BLUETOOTH, BLUETOOTH_CONNECT, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE, READ_CONTACTS, CALL_PHONE, SEND_SMS, POST_NOTIFICATIONS

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Defines the background service that runs service.py
services = sara:service.py:foreground

# Auto-starts Sara when phone boots (if permission granted by OS)
android.manifest.application_arguments = --launch-app

[buildozer]
log_level = 2
warn_on_root = 1