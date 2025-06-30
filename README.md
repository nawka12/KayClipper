# KayClipper

A user-friendly GUI for `yt-dlp` to easily clip and download sections of YouTube videos with customizable quality and format.

![KayClipper Screenshot](https://github.com/user-attachments/assets/31bdd0b6-0243-4ce3-a414-c64eff380c76)

## Features

-   **Easy-to-use Interface**: No command-line knowledge required.
-   **Flexible Downloading**: Download full videos or clip specific sections by leaving start/end times blank.
-   **Automatic Dependency Handling**: Automatically downloads `yt-dlp` and `ffmpeg` on Windows if they are missing.
-   **GPU-Accelerated Encoding**: Utilizes NVIDIA (NVENC), AMD (AMF), or Intel (QSV) GPUs on Windows for faster video processing.
-   **Quality & Format Selection**: Choose from presets like 1080p, 720p, etc., and save as `mp4`, `webm`, `mkv`, and more.
-   **Audio-Only Extraction**: Directly extract audio to `mp3`, `wav`, or `aac`.
-   **Responsive UI**: The app remains responsive while downloading, with a real-time progress bar.

## Prerequisites

-   **Python 3**: [Download Python](https://www.python.org/downloads/)

For **Windows users**, `yt-dlp` and `ffmpeg` are not strictly required beforehand. The application will detect if they are missing and offer to download them for you into a local `bin` folder.

For **macOS and Linux users**, you must install `yt-dlp` and `ffmpeg` manually and ensure they are available in your system's PATH.
-   **yt-dlp**: [Installation instructions](https://github.com/yt-dlp/yt-dlp#installation).
-   **FFmpeg**: [Download FFmpeg](https://ffmpeg.org/download.html) or install via a package manager (e.g., `sudo apt install ffmpeg` or `brew install ffmpeg`).

## Installation

1.  Clone this repository or download the source code.
2.  It's highly recommended to use a Python virtual environment.
    ```bash
    # Create a virtual environment
    python -m venv venv

    # Activate it
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Once the installation is complete, simply run the Python script to launch the application:

```bash
python kay_clipper.py
```

Then, use the interface:
1.  **Paste** the YouTube video URL.
2.  **Enter** the start and end times for your clip (e.g., `00:01:23` or `83` for seconds). You can leave these blank to download from the start or to the end.
3.  **Select** your desired format and quality from the dropdown menus. The quality menu will be disabled for audio-only formats.
4.  **Click "Browse..."** to choose a location and name for your output file.
5.  **Click "Clip Video"**.

The text box at the bottom will show the progress and any success or error messages.

## Building the Executable

For convenience, pre-built executables for Windows are available on the [Releases page](https://github.com/nawka12/KayClipper/releases). If you prefer to build it yourself, follow the steps below.

This project can be packaged into a single `.exe` file for easy distribution on Windows.

1.  **Install all dependencies**, including `pyinstaller`:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the build script**:
    ```bash
    python build.py
    ```

This script will:
-   Automatically download `yt-dlp.exe` and `ffmpeg.exe` into a temporary `bin` folder.
-   Run `PyInstaller` with all the necessary settings to bundle your application, its dependencies, and the required assets into a single file.

The final executable will be located in the `dist` folder, named `KayClipper.exe`.

## How It Works

This application constructs and executes a `yt-dlp` command in the background based on your inputs. It uses multi-threading to ensure the user interface doesn't freeze during the download and clipping process. 

On startup, it detects the user's GPU (on Windows) and will automatically add the correct arguments (`-c:v h264_nvenc`, etc.) to leverage hardware acceleration for video encoding, which significantly speeds up the process. The key `yt-dlp` features it uses are `--download-sections` and `--force-keyframes-at-cuts` for efficient and accurate clipping. 

## License

This project is licensed under the GNU General Public License v3.0. See the [GPL-3.0 License](https://www.gnu.org/licenses/gpl-3.0.html) for details. 
