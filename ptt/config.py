# Audio settings
SAMPLE_RATE = 16000          # Whisper expects 16kHz
CHANNELS = 1                 # Mono
DTYPE = "float32"            # Whisper expects float32 in [-1.0, 1.0]
BLOCK_SIZE = 1024            # Frames per audio callback block

# Whisper settings
WHISPER_MODEL_SIZE = "base"  # Options: tiny, base, small, medium, large-v3
WHISPER_DEVICE = "cpu"       # "cpu" or "cuda"
WHISPER_COMPUTE_TYPE = "int8"  # int8 on CPU for speed; float16 on CUDA
WHISPER_LANGUAGE = "en"      # Set to None for auto-detect
WHISPER_BEAM_SIZE = 1        # 1 = greedy decoding (fastest)

# Streaming transcription settings
STREAM_INTERVAL_MS = 2000    # How often to run partial transcription while recording

# Overlay settings
OVERLAY_WIDTH = 550
OVERLAY_HEIGHT = 250
OVERLAY_BG = "#0f1923"
OVERLAY_FG = "#7eb8e0"
OVERLAY_FG_DIM = "#3d6a8a"
OVERLAY_FONT = ("Segoe UI", 11)
OVERLAY_POSITION = "bottom_right"  # "bottom_right", "top_right", or "center"
OVERLAY_OPACITY = 0.92

# Hotkey
HOTKEY_KEY = "insert"

# Paste delay (ms) — small delay after clipboard write before Ctrl+V
PASTE_DELAY_MS = 50

# Minimum recording duration (seconds) to avoid accidental taps
MIN_RECORDING_DURATION = 0.3

# Double-tap window (seconds) — max time between two taps to trigger recording
DOUBLE_TAP_WINDOW_S = 0.4
