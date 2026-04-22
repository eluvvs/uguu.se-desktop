# Litterbox Desktop & Mobile

A modern, fast, and cross-platform uploader for [Litterbox](https://litterbox.catbox.moe) — select your files, choose an expiration time, hit upload, and get links.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-Unlicense-green)
![Flet](https://img.shields.io/badge/UI-Flet-purple)

## Features

- **Select multiple files** and upload them to Litterbox
- **Expiration Options**: Choose between 1 Hour, 12 Hours, 24 Hours, or 3 Days.
- **High Limit**: Max **1 GB** per file (Litterbox policy)
- **Cross Platform**: Works as a Desktop app (.exe) and an Android app (.apk)
- **Beautiful UI**: Modern purple-themed design built with Flet

## Download

Grab the latest `Litterbox-Windows-EXE` or `Litterbox-Android-APK` from the [Releases](../../releases) page.

## Build from Source

### Requirements
- Python 3.11+
- `pip install .`

### Windows EXE
```bash
flet build windows
```

### Android APK
```bash
flet build apk
```

## Run without Building

```bash
python main.py
```

## How It Works

1. Open the app
2. Choose your preferred **Expiration Time**
3. Click **Add Files** to pick one or more files
4. Click **Upload**
5. Wait for the upload to complete and copy your Litterbox links!

## License

[Unlicense](LICENSE) — public domain.
