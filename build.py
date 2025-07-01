# build.py
import os
import sys
import requests
import zipfile
import io
import shutil
from pathlib import Path

# --- Configuration ---
APP_NAME = "KayClipper"
SCRIPT_FILE = "kay_clipper.py"
BIN_DIR = Path("bin")

# --- URLs for Dependencies ---
FFMPEG_URL_WIN = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def download_and_extract_zip(url, target_dir):
    """Downloads and extracts specific files from a zip archive."""
    print(f"Downloading and extracting from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            for file_info in z.infolist():
                filename = os.path.basename(file_info.filename)
                if filename in ['ffmpeg.exe', 'ffprobe.exe']:
                    print(f"Extracting {filename}...")
                    with z.open(file_info) as source:
                        with open(target_dir / filename, 'wb') as target:
                            shutil.copyfileobj(source, target)
        print("Extraction complete.")
        return True
    except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
        print(f"Error downloading or extracting {url}: {e}", file=sys.stderr)
        return False

def setup_dependencies():
    """Ensures ffmpeg is present in the bin directory for Windows builds."""
    print("--- Checking Dependencies ---")
    BIN_DIR.mkdir(exist_ok=True)

    if sys.platform == "win32":
        # Handle ffmpeg for Windows. yt-dlp is now a Python package dependency
        # and will be handled by PyInstaller automatically.
        ffmpeg_path = BIN_DIR / "ffmpeg.exe"
        ffprobe_path = BIN_DIR / "ffprobe.exe"
        if not ffmpeg_path.exists() or not ffprobe_path.exists():
            print("ffmpeg.exe or ffprobe.exe not found, downloading...")
            if not download_and_extract_zip(FFMPEG_URL_WIN, BIN_DIR):
                sys.exit(1)
        else:
            print("ffmpeg.exe and ffprobe.exe already present in bin/.")
    else:
        # For Linux/macOS, we'll assume ffmpeg is in the PATH.
        # The app itself will handle downloading it if it's missing at runtime.
        print("Assuming 'ffmpeg' is installed and in the system PATH for non-Windows OS.")

    print("--- Dependencies are ready ---")

def build():
    """Builds the executable using PyInstaller."""
    setup_dependencies()
    
    import PyInstaller.__main__
    import customtkinter

    # Find customtkinter path
    customtkinter_path = Path(customtkinter.__file__).parent

    # PyInstaller command arguments
    pyinstaller_args = [
        SCRIPT_FILE,
        f'--name={APP_NAME}',
        '--onefile',
        '--windowed',
        '--clean',
        f'--add-data={BIN_DIR.resolve()};bin',
        f'--add-data={customtkinter_path.resolve()};customtkinter',
    ]

    print("\n--- Running PyInstaller ---")
    print(f"Command: pyinstaller {' '.join(pyinstaller_args)}")
    
    PyInstaller.__main__.run(pyinstaller_args)

    print(f"\n--- Build Complete ---")
    print(f"Executable created at: dist/{APP_NAME}.exe")

if __name__ == "__main__":
    build() 