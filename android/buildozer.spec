[app]
title = T.A.R.A
package.name = tara
package.domain = com.yourname.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# openssl added so requests/gtts work on Android
requirements = python3,kivy==2.3.0,plyer,requests,gtts,certifi,urllib3,charset-normalizer,idna,openssl

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO,SEND_SMS,CALL_PHONE,READ_CONTACTS,WRITE_CONTACTS,READ_PHONE_STATE,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE
android.api = 34
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
