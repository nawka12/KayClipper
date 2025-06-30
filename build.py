# build.py
import os
import sys
import subprocess
import requests
import zipfile
import io
import stat
import shutil
from pathlib import Path

# --- Configuration ---
APP_NAME = "KayClipper"
SCRIPT_FILE = "kay_clipper.py"
BIN_DIR = Path("bin")

# --- URLs for Dependencies ---
YT_DLP_URL_WIN = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
YT_DLP_URL_NIX = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
FFMPEG_URL_WIN = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

def download_file(url, path):
    """Downloads a file and saves it to a given path."""
    print(f"Downloading {url} to {path}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False

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
    """Ensures yt-dlp and ffmpeg are present in the bin directory."""
    print("--- Checking Dependencies ---")
    BIN_DIR.mkdir(exist_ok=True)

    if sys.platform == "win32":
        # Handle yt-dlp for Windows
        yt_dlp_path = BIN_DIR / "yt-dlp.exe"
        if not yt_dlp_path.exists():
            if not download_file(YT_DLP_URL_WIN, yt_dlp_path):
                sys.exit(1)

        # Handle ffmpeg for Windows
        ffmpeg_path = BIN_DIR / "ffmpeg.exe"
        if not ffmpeg_path.exists():
            if not download_and_extract_zip(FFMPEG_URL_WIN, BIN_DIR):
                sys.exit(1)
    else:
        # Handle yt-dlp for Linux/macOS
        yt_dlp_path = BIN_DIR / "yt-dlp"
        if not yt_dlp_path.exists():
            if not download_file(YT_DLP_URL_NIX, yt_dlp_path):
                sys.exit(1)
            # Make it executable
            st = os.stat(yt_dlp_path)
            os.chmod(yt_dlp_path, st.st_mode | stat.S_IEXEC)
        
        # For Linux/macOS, we'll assume ffmpeg is in the PATH.
        # Bundling it is more complex due to system variations.
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