import sys
import os
from pathlib import Path
from cx_Freeze import setup, Executable

# Bundle MSVC++ runtime DLLs so the app works on machines without the redist installed
_msvc_dlls = []
_python_dir = Path(sys.base_prefix)
_sys32 = Path(os.environ["SYSTEMROOT"]) / "System32"

for dll_name in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"):
    # Prefer the copy from the Python install, fall back to System32
    for search_dir in (_python_dir, _sys32):
        dll_path = search_dir / dll_name
        if dll_path.exists():
            _msvc_dlls.append(str(dll_path))
            break

build_exe_options = {
    "packages": [
        "ptt",
        "faster_whisper",
        "ctranslate2",
        "sounddevice",
        "numpy",
        "pynput",
        "pystray",
        "PIL",
    ],
    "bin_includes": _msvc_dlls,
    "include_files": [
        ("assets", "assets"),
    ],
    "excludes": [
        "test",
        "unittest",
    ],
}

# Fixed upgrade_code ensures MSI upgrades replace old versions
bdist_msi_options = {
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\PTT",
    "upgrade_code": "{A7E3B4D1-9F2C-4E8A-B6D5-1C3F7A2E9D04}",
    "data": {
        # Directory table: define a Start Menu subfolder
        "Directory": [
            ("ProgramMenuFolder", "TARGETDIR", "."),
            ("PTTStartMenu", "ProgramMenuFolder", "PTT~1|Push-to-Talk"),
        ],
    },
}

icon_path = Path("assets/icon.ico")
icon_arg = str(icon_path) if icon_path.exists() else None

# Two executables entries: one for Desktop shortcut, one for Start Menu
executables = [
    Executable(
        script="run.py",
        base="gui" if sys.platform == "win32" else None,
        target_name="PTT.exe",
        icon=icon_arg,
        shortcut_name="Push-to-Talk",
        shortcut_dir="PTTStartMenu",
    )
]

setup(
    name="PTT",
    version="1.1.0",
    description="Push-to-Talk Voice-to-Text",
    author="stoate",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables,
)
