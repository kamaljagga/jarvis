# -*- mode: python ; coding: utf-8 -*-
# ═══════════════════════════════════════════════
#  J.A.R.V.I.S — PyInstaller Spec File
#  Builds a single .exe with everything bundled.
#  Run: pyinstaller jarvis.spec
# ═══════════════════════════════════════════════

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all hidden imports (packages that PyInstaller misses)
hidden = [
    'pyttsx3', 'pyttsx3.drivers', 'pyttsx3.drivers.sapi5',
    'speech_recognition',
    'sounddevice', 'soundfile',
    'pyautogui', 'pywhatkit',
    'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
    'gtts', 'gtts.tts',
    'playsound',
    'psutil', 'psutil._pswindows',
    'pycaw', 'comtypes', 'comtypes.client',
    'pyperclip',
    'vosk',
    'numpy', 'numpy.core', 'numpy.lib',
    'winreg',
    'json', 'threading', 'subprocess', 'ctypes',
    'webbrowser', 'datetime', 're', 'math', 'random',
]

# Collect data files (vosk needs its model, gtts needs cacerts, etc.)
datas = []
datas += collect_data_files('gtts')
datas += collect_data_files('speech_recognition')

# Include vosk model if present
if os.path.exists('model'):
    datas.append(('model', 'model'))

# Include settings, contacts JSON if present
for f in ['settings.json', 'contacts.json']:
    if os.path.exists(f):
        datas.append((f, '.'))

a = Analysis(
    ['main_ai.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PIL', 'cv2', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Jarvis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # compress EXE (smaller size)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # set False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',   # optional: your icon file
    version='version_info.txt',  # optional: version info
)
