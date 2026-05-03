[app]
title = J.A.R.V.I.S
package.name = jarvis
package.domain = com.yourname.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy==2.3.0,plyer,requests,gtts,certifi,urllib3,charset-normalizer,idna
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO,SEND_SMS,CALL_PHONE,READ_CONTACTS,WRITE_CONTACTS,READ_PHONE_STATE,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,FOREGROUND_SERVICE,FOREGROUND_SERVICE_MICROPHONE,USE_FULL_SCREEN_INTENT

android.sdk_build_tools_version = 34.0.0
android.api = 34
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
