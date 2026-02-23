# Push-to-Talk Voice-to-Text

A Windows push-to-talk app that transcribes your speech and pastes it into any application. Double-tap **Insert** (or **Right Ctrl**) to start recording, tap again to stop and paste. Uses a local Whisper model — no API keys, no cloud, fully offline.

## Download

**[Download PTT-1.1.0-win64.msi](https://github.com/brontoguana/windows-ptt/releases/download/v1.1.0/PTT-1.1.0-win64.msi)**

Run the installer and launch "Push-to-Talk" from the Start Menu. The first launch downloads the Whisper model (~150 MB).

## Features

- **Double-tap to talk** — Double-tap Insert or Right Ctrl to record, tap once more to transcribe and paste
- **Live transcription** — See your words appear in a floating overlay as you speak
- **Cancel with ESC** — Press Escape while recording to discard
- **Works everywhere** — Pastes into whatever app has focus (Notepad, browser, Slack, etc.)
- **Fully offline** — Runs a local Whisper model, no internet needed after first setup
- **Lightweight** — Sits quietly in the system tray until you need it
- **Single instance** — Launching again cleanly replaces the running copy

## Usage

| Action | Key | Result |
|--------|-----|--------|
| Start recording | Double-tap **Insert** or **Right Ctrl** | Overlay appears, mic starts capturing |
| Finish & paste | Tap **Insert** or **Right Ctrl** | Text is transcribed and pasted |
| Cancel | Press **ESC** while recording | Recording discarded, nothing pasted |
| Quit | Right-click tray icon → Quit | App exits |

## Building from Source

Requires **Python 3.12 or 3.14** on Windows (Python 3.13 is not supported due to a missing ctranslate2 wheel).

```bash
# Create virtual environment
py -3.14 -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate the tray icon
python generate_icon.py

# Run
python run.py
```

## Configuration

Edit `ptt/config.py` to customise:

| Setting | Default | Description |
|---------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `"base"` | Model size: tiny, base, small, medium, large-v3 |
| `WHISPER_DEVICE` | `"cpu"` | `"cpu"` or `"cuda"` for GPU acceleration |
| `WHISPER_LANGUAGE` | `"en"` | Language code, or `None` for auto-detect |
| `OVERLAY_POSITION` | `"bottom_right"` | `"bottom_right"`, `"top_right"`, or `"center"` |
| `STREAM_INTERVAL_MS` | `2000` | How often live transcription updates (ms) |
| `DOUBLE_TAP_WINDOW_S` | `0.4` | Max seconds between taps to trigger recording |

## Building the MSI Installer

```bash
python setup_cx.py bdist_msi
```

Output: `dist/PTT-1.1.0-win64.msi`

## License

All rights reserved.
