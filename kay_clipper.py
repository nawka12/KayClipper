import customtkinter as ctk
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox
import os
import requests
import zipfile
import io
import stat
import re

# --- Appearance ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class KayClipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KayClipper - YouTube Video Clipper")
        self.geometry("700x580") # Increased height for progress bar
        self.grid_columnconfigure(0, weight=1)

        # --- App State ---
        self.bin_dir = get_resource_path("bin")
        os.makedirs(self.bin_dir, exist_ok=True)
        
        yt_dlp_exe = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
        ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
        self.yt_dlp_path = os.path.join(self.bin_dir, yt_dlp_exe)
        self.ffmpeg_path = os.path.join(self.bin_dir, ffmpeg_exe)
        
        self.deps_ok = False
        self.gpu_codec = None
        self.gpu_vendor = None

        # --- Widgets ---
        self.create_widgets()
        self.check_dependencies()
        threading.Thread(target=self._detect_gpu, daemon=True).start()

    def create_widgets(self):
        # --- Main Frame ---
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(1, weight=1)

        # --- URL Entry ---
        ctk.CTkLabel(main_frame, text="YouTube URL:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = ctk.CTkEntry(main_frame, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Time Entries ---
        ctk.CTkLabel(main_frame, text="Start Time:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.start_time_entry = ctk.CTkEntry(main_frame, placeholder_text="HH:MM:SS (optional, from start)")
        self.start_time_entry.grid(row=1, column=1, padx=(10, 5), pady=10, sticky="ew")

        ctk.CTkLabel(main_frame, text="End Time:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.end_time_entry = ctk.CTkEntry(main_frame, placeholder_text="HH:MM:SS (optional, to end)")
        self.end_time_entry.grid(row=2, column=1, padx=(10, 5), pady=10, sticky="ew")

        # --- Format and Quality ---
        ctk.CTkLabel(main_frame, text="Format:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.format_menu = ctk.CTkOptionMenu(main_frame, values=["mp4", "webm", "mkv", "mp3", "wav", "aac"], command=self.toggle_quality_menu)
        self.format_menu.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(main_frame, text="Quality:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.quality_menu = ctk.CTkOptionMenu(main_frame, values=["Best", "1080p", "720p", "480p", "360p"])
        self.quality_menu.grid(row=4, column=1, padx=10, pady=10, sticky="w")

        # --- Output Path ---
        ctk.CTkLabel(main_frame, text="Save As:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        self.output_path_entry = ctk.CTkEntry(main_frame, placeholder_text="Click 'Browse' to select a location")
        self.output_path_entry.grid(row=5, column=1, padx=10, pady=10, sticky="ew")
        self.browse_button = ctk.CTkButton(main_frame, text="Browse...", command=self.browse_output_path)
        self.browse_button.grid(row=5, column=2, padx=(0, 10), pady=10)

        # --- Clip Button ---
        self.clip_button = ctk.CTkButton(self, text="Checking Dependencies...", command=self.start_clipping_thread)
        self.clip_button.configure(state="disabled")
        self.clip_button.grid(row=1, column=0, padx=20, pady=10)

        # --- Progress Bar (now permanent) ---
        self.progress_bar = ctk.CTkProgressBar(self, orientation="horizontal")
        self.progress_bar.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        # --- Progress/Output Console ---
        self.output_console = ctk.CTkTextbox(self, height=150, state="disabled")
        self.output_console.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def toggle_quality_menu(self, selected_format):
        """Enable or disable the quality dropdown based on the selected format."""
        if selected_format in ["mp3", "wav", "aac"]:
            self.quality_menu.configure(state="disabled")
        else:
            self.quality_menu.configure(state="normal")

    def log_message(self, message, is_error=False):
        """Append a message to the output console."""
        self.output_console.configure(state="normal")
        tag = "error" if is_error else "info"
        self.output_console.tag_config("error", foreground="red")
        self.output_console.insert("end", f"{message}\n", tag)
        self.output_console.configure(state="disabled")
        self.output_console.see("end")

    def browse_output_path(self):
        """Open a file dialog to choose the output file path."""
        file_format = self.format_menu.get()
        file_types = [(f"{file_format.upper()} file", f"*.{file_format}")]
        
        output_path = filedialog.asksaveasfilename(
            title="Save Clip As",
            filetypes=file_types,
            defaultextension=f".{file_format}"
        )
        if output_path:
            self.output_path_entry.delete(0, "end")
            self.output_path_entry.insert(0, output_path)

    def get_quality_string(self):
        """Get the yt-dlp format string based on user selection."""
        quality = self.quality_menu.get()
        video_format = self.format_menu.get()
        
        if video_format in ['mp3', 'wav', 'aac']:
            return "bestaudio/best"

        quality_map = {
            "Best": f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "1080p": f"bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "720p": f"bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "480p": f"bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "360p": f"bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        }
        return quality_map.get(quality, "best")


    def check_dependencies(self):
        """Check for yt-dlp and ffmpeg on a background thread."""
        threading.Thread(target=self._check_dependencies_and_prompt, daemon=True).start()

    def _check_dependencies_and_prompt(self):
        """Check for dependencies and prompt user to download if missing."""
        self.log_message("🔎 Checking for dependencies...")
        yt_dlp_ok = False
        ffmpeg_ok = False

        # --- Check for yt-dlp ---
        try:
            # Check local bin directory first
            subprocess.run([self.yt_dlp_path, '--version'], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            yt_dlp_ok = True
            self.log_message("✅ yt-dlp found locally.")
        except (OSError, subprocess.CalledProcessError):
            try:
                # If not found or not working, check system PATH
                subprocess.run(['yt-dlp', '--version'], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                self.yt_dlp_path = 'yt-dlp'  # Use system version
                yt_dlp_ok = True
                self.log_message("✅ yt-dlp found in system PATH.")
            except (OSError, subprocess.CalledProcessError):
                self.log_message("❌ yt-dlp not found.", is_error=True)
                self.after(0, lambda: self.prompt_download("yt-dlp"))

        # --- Check for ffmpeg ---
        try:
            # Check local bin directory first
            subprocess.run([self.ffmpeg_path, '-version'], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            ffmpeg_ok = True
            self.log_message("✅ FFmpeg found locally.")
        except (OSError, subprocess.CalledProcessError):
            try:
                # If not found or not working, check system PATH
                subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                self.ffmpeg_path = 'ffmpeg'  # Use system version
                ffmpeg_ok = True
                self.log_message("✅ FFmpeg found in system PATH.")
            except (OSError, subprocess.CalledProcessError):
                self.log_message("❌ FFmpeg not found.", is_error=True)
                self.after(0, lambda: self.prompt_download("ffmpeg"))

        if yt_dlp_ok and ffmpeg_ok:
            self.deps_ok = True
            self.after(0, self.on_deps_ready)

    def on_deps_ready(self):
        """Callback executed when dependencies are confirmed to be ready."""
        self.log_message("✅ All dependencies are ready.")
        self.clip_button.configure(state="normal", text="Clip Video")
        self.deps_ok = True

    def reset_ui_state(self):
        """Resets the button and progress bar."""
        self.clip_button.configure(state="normal", text="Clip Video")
        self.progress_bar.set(0)

    def prompt_download(self, dependency_name):
        """Ask user if they want to download a missing dependency."""
        answer = messagebox.askyesno(
            "Dependency Not Found",
            f"'{dependency_name}' is missing. This is required for the app to function.\n\n"
            f"Do you want to download it automatically? It will be saved in the 'bin' folder."
        )
        if not answer:
            self.log_message(f"❌ Download for {dependency_name} cancelled by user.", is_error=True)
            return

        downloader = self.download_yt_dlp if dependency_name == "yt-dlp" else self.download_ffmpeg
        threading.Thread(target=downloader, daemon=True).start()

    def download_yt_dlp(self):
        """Downloads the latest yt-dlp executable."""
        self.log_message("⬇️ Downloading yt-dlp...")
        try:
            url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" if sys.platform == "win32" else "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(self.yt_dlp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if sys.platform != "win32":
                st = os.stat(self.yt_dlp_path)
                os.chmod(self.yt_dlp_path, st.st_mode | stat.S_IEXEC)

            self.log_message("✅ yt-dlp downloaded successfully.")
            # Re-run the dependency check to confirm and enable the button
            self._check_dependencies_and_prompt()
        except Exception as e:
            self.log_message(f"❌ Failed to download yt-dlp: {e}", is_error=True)

    def download_ffmpeg(self):
        """Downloads and extracts ffmpeg."""
        self.log_message("⬇️ Downloading FFmpeg (this may take a moment)...")
        try:
            if sys.platform == "win32":
                url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            else:  # Assuming linux, macOS users might have it via package manager
                self.log_message("Please install FFmpeg using your system's package manager (e.g., 'sudo apt install ffmpeg' or 'brew install ffmpeg').", is_error=True)
                return

            response = requests.get(url, stream=True)
            response.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                extracted_ffmpeg = False
                for file_info in z.infolist():
                    # Look for ffmpeg.exe and ffprobe.exe inside a 'bin' folder in the zip
                    filename = os.path.basename(file_info.filename)
                    if filename == 'ffmpeg.exe':
                        with z.open(file_info) as source, open(self.ffmpeg_path, 'wb') as target:
                            target.write(source.read())
                        extracted_ffmpeg = True
                    elif filename == 'ffprobe.exe':
                        ffprobe_path = os.path.join(self.bin_dir, "ffprobe.exe")
                        with z.open(file_info) as source, open(ffprobe_path, 'wb') as target:
                            target.write(source.read())

                if not extracted_ffmpeg:
                    raise FileNotFoundError("Could not find ffmpeg.exe in the downloaded archive.")

            self.log_message("✅ FFmpeg downloaded and extracted successfully.")
            # Re-run the dependency check to confirm and enable the button
            self._check_dependencies_and_prompt()
        except Exception as e:
            self.log_message(f"❌ Failed to download FFmpeg: {e}", is_error=True)

    def _detect_gpu(self):
        """Detect GPU on Windows to enable hardware acceleration."""
        self.log_message("🔎 Detecting GPU for hardware acceleration...")
        if sys.platform != "win32":
            self.log_message("ℹ️ GPU detection is only supported on Windows.")
            return

        gpu_name = ""
        # Try PowerShell first (more modern and reliable)
        try:
            flags = subprocess.CREATE_NO_WINDOW
            command = [
                'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
                "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name"
            ]
            result = subprocess.run(command, check=True, capture_output=True, text=True, creationflags=flags)
            gpu_name = result.stdout.lower()
            self.log_message("ℹ️ GPU detection using PowerShell successful.")
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Fallback to WMIC if PowerShell fails
            self.log_message("⚠️ PowerShell method failed, falling back to WMIC.")
            try:
                flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    check=True, capture_output=True, text=True, creationflags=flags
                )
                gpu_name = result.stdout.lower()
                self.log_message("ℹ️ GPU detection using WMIC successful.")
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.log_message("❌ Could not detect GPU using PowerShell or WMIC. Using CPU for encoding.", is_error=True)
                return

        if 'nvidia' in gpu_name:
            self.gpu_vendor = "NVIDIA"
            self.gpu_codec = "h264_nvenc"
        elif 'amd' in gpu_name:
            self.gpu_vendor = "AMD"
            self.gpu_codec = "h264_amf"
        elif 'intel' in gpu_name:
            self.gpu_vendor = "Intel"
            self.gpu_codec = "h264_qsv"
        
        if self.gpu_vendor:
            self.log_message(f"✅ {self.gpu_vendor} GPU detected. Will attempt hardware acceleration.")
        else:
            self.log_message("ℹ️ No supported GPU for hardware acceleration was found. Using CPU.")

    def parse_time_to_seconds(self, time_str):
        """Converts HH:MM:SS or seconds string to total seconds. Returns None on error."""
        if not time_str:
            return 0  # Treat empty string as 0 for comparison
        try:
            if ':' in time_str:
                parts = time_str.split(':')
                seconds = 0
                for i, part in enumerate(reversed(parts)):
                    seconds += float(part) * (60 ** i)
                return seconds
            else:
                return float(time_str)
        except (ValueError, TypeError):
            return None

    def start_clipping_thread(self):
        """Start the clipping process in a separate thread to keep the GUI responsive."""
        self.clip_button.configure(state="disabled", text="Clipping...")
        self.progress_bar.set(0)
        thread = threading.Thread(target=self.clip_video, daemon=True)
        thread.start()

    def update_progress(self, value):
        """Update the progress bar value."""
        self.progress_bar.set(value)

    def clip_video(self):
        """The main clipping logic."""
        # --- Get user inputs ---
        url = self.url_entry.get()
        start_time_str = self.start_time_entry.get().strip()
        end_time_str = self.end_time_entry.get().strip()
        video_format = self.format_menu.get()
        quality = self.get_quality_string()
        output_filename = self.output_path_entry.get()

        # --- Validate inputs ---
        if not url or not output_filename:
            self.log_message("❌ Error: Please provide a video URL and select an output file.", is_error=True)
            self.after(0, self.reset_ui_state)
            return

        # --- Time Validation ---
        start_seconds = self.parse_time_to_seconds(start_time_str)
        end_seconds = self.parse_time_to_seconds(end_time_str)

        if start_seconds is None:
            self.log_message(f"❌ Error: Invalid start time format: '{start_time_str}'.", is_error=True)
            self.after(0, self.reset_ui_state)
            return
        if end_seconds is None:
            self.log_message(f"❌ Error: Invalid end time format: '{end_time_str}'.", is_error=True)
            self.after(0, self.reset_ui_state)
            return

        if start_time_str and end_time_str and start_seconds >= end_seconds:
            self.log_message("❌ Error: Start time must be less than end time.", is_error=True)
            self.after(0, self.reset_ui_state)
            return

        # --- Build Command ---
        command = [self.yt_dlp_path]
        
        # Tell yt-dlp where ffmpeg is, especially if we downloaded it
        command.extend(['--ffmpeg-location', self.bin_dir])
        
        # Add download sections for clipping if a time range is specified
        if start_time_str or end_time_str:
            command.extend(['--download-sections', f"*{start_time_str}-{end_time_str}"])
            # Force ffmpeg for accurate seeking only when clipping
            command.extend(['--force-keyframes-at-cuts'])

        # Format selection
        command.extend(['-f', quality])

        # Recode if necessary
        is_audio_only = video_format in ['mp3', 'wav', 'aac']
        if is_audio_only:
            command.extend(['--extract-audio', '--audio-format', video_format])
        else:
            # For video, always recode to ensure the format is correct
            command.extend(['--recode-video', video_format])
            if self.gpu_codec:
                # If a supported GPU is found, add the necessary args for hardware encoding
                self.log_message(f"🚀 Using {self.gpu_vendor} GPU for faster processing.")
                command.extend(['--postprocessor-args', f'VideoConvertor:-c:v {self.gpu_codec}'])

        # Output
        command.extend(['-o', output_filename, url])
        
        # Suppress verbose output
        command.extend(['--quiet', '--progress', '--no-warnings'])

        # --- Execute Command ---
        self.log_message(f"▶️ Starting clip for: {url}")
        
        try:
            # Using CREATE_NO_WINDOW to prevent console popup on Windows
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            
            # Real-time progress parsing from stdout
            for line in iter(process.stdout.readline, ''):
                match = re.search(r"\[download\]\s+([0-9\.]+)%", line)
                if match:
                    percent = float(match.group(1))
                    self.after(0, self.update_progress, percent / 100.0)

            # Wait for the process to finish and get the output
            stderr = process.stderr.read()
            process.wait()

            if process.returncode == 0:
                self.log_message(f"✅ Success! Clip saved to: {output_filename}")
                self.after(0, self.update_progress, 1.0) # Set to 100% on success
            else:
                self.log_message(f"❌ Error during clipping process.", is_error=True)
                if stderr:
                    self.log_message(f"Details: {stderr.strip()}", is_error=True)

        except FileNotFoundError:
            self.log_message("❌ Error: yt-dlp or ffmpeg not found. Please ensure they are installed and in your PATH.", is_error=True)
        except Exception as e:
            self.log_message(f"❌ An unexpected error occurred: {e}", is_error=True)
        finally:
            # Re-enable the button and hide progress bar on the main thread
            self.after(0, self.reset_ui_state)


if __name__ == "__main__":
    app = KayClipperApp()
    app.mainloop() 