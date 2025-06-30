# KayClipper

A user-friendly GUI for `yt-dlp` to easily clip and download sections of YouTube videos with customizable quality and format.

![KayClipper Screenshot](https_placeholder_for_screenshot.png) 
*(A screenshot would go here)*

## Features

-   **Easy-to-use Interface**: No command-line knowledge required.
-   **Clip Videos**: Specify start and end times to download only the part you need.
-   **Quality Selection**: Choose from presets like 1080p, 720p, etc., or just "Best".
-   **Format Choice**: Save as `mp4`, `webm`, `mkv`, and more.
-   **Audio Only**: Directly extract audio to `mp3`, `wav`, or `aac`.
-   **Background Processing**: The app remains responsive while downloading.
-   **Dependency Checks**: The app checks for `yt-dlp` and `ffmpeg` on startup.

## Prerequisites

Before using KayClipper, you need to have the following installed and available in your system's PATH:

1.  **Python 3**: [Download Python](https://www.python.org/downloads/)
2.  **yt-dlp**: The core tool for downloading. [Installation instructions](https://github.com/yt-dlp/yt-dlp#installation).
3.  **FFmpeg**: Required by `yt-dlp` for any kind of clipping or format conversion. [Download FFmpeg](https://ffmpeg.org/download.html).

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
2.  **Enter** the start and end times for your clip (e.g., `00:01:23` or `83` for seconds).
3.  **Select** your desired format and quality from the dropdown menus.
4.  **Click "Browse..."** to choose a location and name for your output file.
5.  **Click "Clip Video"**.

The text box at the bottom will show the progress and any success or error messages.

## Building the Executable

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

This application builds and executes a `yt-dlp` command in the background based on your inputs. It uses multi-threading to ensure the user interface doesn't freeze during the download and clipping process. The key `yt-dlp` features it uses are `--download-sections` and `--force-keyframes-at-cuts` for efficient and accurate clipping. 