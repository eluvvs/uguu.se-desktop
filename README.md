# Uguu Desktop

A tiny, lightweight desktop uploader for [uguu.se](https://uguu.se) — select your files, hit upload, get links.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-Unlicense-green)

## Features

- **Select multiple files** and upload them to uguu.se
- **Click any link** to copy it to clipboard
- **No dependencies** beyond Python's standard library (tkinter + urllib)
- **Single .exe** — no installer needed, just download and run
- Files expire after **3 hours** (uguu.se policy)
- Max **128 MiB** per file

## Download

Grab the latest `UguuDesktop.exe` from the [Releases](../../releases) page.

## Build from Source

```bash
pip install -r requirements.txt
pyinstaller uguu_desktop.spec
```

The built exe will be in `dist/UguuDesktop.exe`.

## Run without Building

```bash
python uguu_desktop.py
```

## How It Works

1. Open the app
2. Click **Add Files** to pick one or more files
3. Click **Upload**
4. Click any returned link to copy it to your clipboard

## License

[Unlicense](LICENSE) — public domain.
