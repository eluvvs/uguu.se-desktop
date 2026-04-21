# -*- mode: python ; coding: utf-8 -*-
import os
import tkinterdnd2

# Bundle the tkdnd native library alongside the exe
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# Modules we never use — excluding them shrinks the bundle
# and speeds up extraction (= faster startup)
EXCLUDES = [
    # Testing
    'unittest', 'pytest', 'doctest', 'test',
    # Dev tools
    'pdb', 'pydoc', 'profile', 'cProfile', 'trace',
    # Unused stdlib
    'xml', 'xmlrpc', 'html.parser', 'plistlib',
    'sqlite3', 'decimal', 'fractions', 'statistics',
    'csv', 'configparser', 'tomllib',
    'logging', 'gettext', 'argparse', 'optparse',
    'multiprocessing', 'concurrent', 'asyncio',
    'socketserver', 'ftplib', 'smtplib', 'imaplib',
    'poplib', 'nntplib', 'telnetlib',
    'turtle', 'turtledemo', 'tkinter.tix',
    'distutils', 'setuptools', 'pkg_resources', 'pip',
    'lib2to3', 'ensurepip', 'venv', 'idlelib',
    'curses', 'readline',
    'mailbox', 'mailcap', 'calendar', 'pprint',
    'pickletools', 'py_compile', 'compileall',
    'zipapp', 'zipimport',
    # Crypto/hash we don't need
    'hmac', 'secrets',
    # Pillow (not needed at runtime)
    'PIL', 'Pillow',
]

a = Analysis(
    ['uguu_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('imgs/favicon.ico', 'imgs'),
        (tkdnd_path, 'tkinterdnd2'),
    ],
    hiddenimports=['tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='UguuDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='imgs/favicon.ico',
)
