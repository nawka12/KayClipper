# KayClipper

A user-friendly GUI for `yt-dlp` to easily clip and download sections of YouTube videos with customizable quality and format.

![KayClipper Screenshot](https://github.com/user-attachments/assets/31bdd0b6-0243-4ce3-a414-c64eff380c76)

## Features

-   **Easy-to-use Interface**: No command-line knowledge required.
-   **Flexible Downloading**: Download full videos or clip specific sections by leaving start/end times blank.
-   **Automatic FFmpeg Handling**: The application will detect if `ffmpeg` is missing and offer to download it automatically, ensuring it works out-of-the-box on any OS.
-   **GPU-Accelerated Encoding**: Utilizes NVIDIA (NVENC), AMD (AMF), or Intel (QSV) GPUs on Windows for faster video processing.
-   **Quality & Format Selection**: Choose from presets like 1080p, 720p, etc., and save as `mp4`, `webm`, `mkv`, and more.
-   **Audio-Only Extraction**: Directly extract audio to `mp3`, `wav`, or `aac`.
-   **Responsive UI**: The app remains responsive while downloading, with a real-time progress bar.

## Prerequisites

-   **Python 3**: [Download Python](https://www.python.org/downloads/)
-   **FFmpeg** (Optional): While the app can download `ffmpeg` for you, having it pre-installed on your system (and available in your PATH) can be more reliable. You can install it via a package manager (e.g., `sudo apt install ffmpeg` or `brew install ffmpeg`).

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
3.  Install the required Python packages, which includes `yt-dlp`:
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

This project can be packaged into a single `.exe` file for easy distribution.

1.  **Install all dependencies**, including `pyinstaller`:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the build script**:
    ```bash
    python build.py
    ```

This script will:
-   On Windows, automatically download `ffmpeg.exe` and `ffprobe.exe` into a `bin` folder if they are missing. This folder will be bundled with the app.
-   Run `PyInstaller` with all the necessary settings to bundle the application, its Python dependencies (like `yt-dlp` and `customtkinter`), and the required assets into a single file.

The final executable will be located in the `dist` folder.

## How It Works

This application uses the `yt-dlp` Python library to handle the downloading and processing of videos. It constructs a dictionary of options based on your inputs and passes it to `yt-dlp`'s main function. This provides more robust integration than calling the command-line tool.

The application runs the clipping process in a separate thread to ensure the user interface remains responsive. Progress hooks from `yt-dlp` are used to update the progress bar in real-time.

On startup, it detects the user's GPU (on Windows) and will automatically add the correct `ffmpeg` arguments to the `yt-dlp` options. This leverages hardware acceleration for both decoding and encoding (`-hwaccel cuda`, `-c:v h264_nvenc`, etc.), which significantly speeds up the transcoding process by keeping the video frames on the GPU.

## License

This project is licensed under the GNU General Public License v3.0. See the [GPL-3.0 License](https://www.gnu.org/licenses/gpl-3.0.html) for details. 
