[app]
title = Sara Assistant
package.name = sara
package.domain = com.yourname
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 1.0

# Added kivymd, jnius, and backend libs
requirements = python3,kivy==2.3.0,kivymd,jnius,plyer,requests,gtts,certifi,urllib3,charset-normalizer,idna,openssl,android

orientation = portrait
fullscreen = 1

# Extensive permissions for hardware and background services
android.permissions = INTERNET,RECORD_AUDIO,CAMERA,SET_ALARM,BLUETOOTH,BLUETOOTH_CONNECT,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,READ_CONTACTS,CALL_PHONE,SEND_SMS

android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Define the background service (Name: filename: foreground: type)
services = sara:service.py:foreground:microphone

android.manifest.application_arguments = --launch-app
