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
import yt_dlp
import shutil

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
        
        ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        
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
        """Check for ffmpeg on a background thread."""
        threading.Thread(target=self._check_dependencies_and_prompt, daemon=True).start()

    def _check_dependencies_and_prompt(self):
        """Check for dependencies and prompt user to download if missing."""
        self.log_message("🔎 Checking for dependencies...")
        # yt-dlp is now a package, so we only need to check for ffmpeg
        ffmpeg_ok = False

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

        if ffmpeg_ok:
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
        
        if dependency_name == "ffmpeg":
            threading.Thread(target=self.download_ffmpeg, daemon=True).start()

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
                extracted_ffprobe = False
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
                        extracted_ffprobe = True

                if not extracted_ffmpeg or not extracted_ffprobe:
                    raise FileNotFoundError("Could not find ffmpeg.exe and/or ffprobe.exe in the downloaded archive.")

            self.log_message("✅ FFmpeg and ffprobe downloaded and extracted successfully.")
            # Re-run the dependency check to confirm and enable the button
            self._check_dependencies_and_prompt()
        except Exception as e:
            self.log_message(f"❌ Failed to download FFmpeg: {e}", is_error=True)

    def _detect_gpu(self):
        """Detect GPU and select appropriate encoder/flags per OS."""
        self.log_message("🔎 Detecting GPU for hardware acceleration...")
        if sys.platform == "win32":
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
            elif 'amd' in gpu_name or 'advanced micro devices' in gpu_name or 'ati' in gpu_name:
                self.gpu_vendor = "AMD"
                self.gpu_codec = "h264_amf"
            elif 'intel' in gpu_name:
                self.gpu_vendor = "Intel"
                self.gpu_codec = "h264_qsv"

        elif sys.platform.startswith("linux"):
            # Prefer direct NVIDIA query if available
            try:
                if shutil.which('nvidia-smi'):
                    result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                            check=True, capture_output=True, text=True)
                    if result.stdout.strip():
                        self.gpu_vendor = "NVIDIA"
                        self.gpu_codec = "h264_nvenc"
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

            # If not NVIDIA, fall back to lspci to detect Intel/AMD
            if not self.gpu_vendor:
                try:
                    if shutil.which('lspci'):
                        result = subprocess.run(['lspci', '-nnk'], check=True, capture_output=True, text=True)
                        gpu_info = result.stdout.lower()
                        if any(v in gpu_info for v in ['amd', 'advanced micro devices', 'ati']):
                            self.gpu_vendor = "AMD"
                            self.gpu_codec = "h264_vaapi"
                        elif 'intel' in gpu_info:
                            self.gpu_vendor = "Intel"
                            self.gpu_codec = "h264_vaapi"
                except (FileNotFoundError, subprocess.CalledProcessError):
                    pass

            if not self.gpu_vendor:
                self.log_message("ℹ️ No discrete GPU detected or utilities missing; will use CPU.")
                return

        else:
            # Other OS (e.g., macOS) not currently handled explicitly
            self.log_message("ℹ️ GPU detection not implemented for this OS. Using CPU.")
            return

        if self.gpu_vendor:
            self.log_message(f"✅ {self.gpu_vendor} GPU detected. Will attempt hardware acceleration.")
        else:
            self.log_message("ℹ️ No supported GPU for hardware acceleration was found. Using CPU.")

    def _find_vaapi_device(self):
        """Return a usable VA-API render node path if present, else None."""
        dri_dir = '/dev/dri'
        default_render = os.path.join(dri_dir, 'renderD128')
        if os.path.exists(default_render):
            return default_render
        if os.path.isdir(dri_dir):
            try:
                for entry in sorted(os.listdir(dri_dir)):
                    if entry.startswith('renderD'):
                        candidate = os.path.join(dri_dir, entry)
                        if os.path.exists(candidate):
                            return candidate
            except Exception:
                return None
        return None

    def parse_time_to_seconds(self, time_str):
        """Converts HH:MM:SS or seconds string to total seconds. Returns None on error or empty string."""
        if not time_str:
            return None
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

    class YTDLLogger:
        def __init__(self, app_instance):
            self.app = app_instance

        def debug(self, msg):
            # For now, we ignore debug messages from yt-dlp
            if msg.startswith('[debug] '):
                pass
            else:
                self.info(msg)

        def info(self, msg):
            # You can decide if you want to show these in your console
            pass

        def warning(self, msg):
            self.app.log_message(f"⚠️ {msg}")

        def error(self, msg):
            self.app.log_message(f"❌ {msg}", is_error=True)

    def update_progress(self, d):
        """Hook for yt-dlp to update the progress bar."""
        if d['status'] == 'downloading':
            p = d['_percent_str']
            p = p.replace('%','').strip()
            try:
                percent = float(p)
                self.after(0, self.progress_bar.set, percent / 100.0)
            except ValueError:
                # Handle cases where percentage is not a number
                pass
        if d['status'] == 'finished':
            self.after(0, self.progress_bar.set, 1.0)

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

        if start_time_str and start_seconds is None:
            self.log_message(f"❌ Error: Invalid start time format: '{start_time_str}'.", is_error=True)
            self.after(0, self.reset_ui_state)
            return
        if end_time_str and end_seconds is None:
            self.log_message(f"❌ Error: Invalid end time format: '{end_time_str}'.", is_error=True)
            self.after(0, self.reset_ui_state)
            return

        if start_seconds is not None and end_seconds is not None and start_seconds >= end_seconds:
            self.log_message("❌ Error: Start time must be less than end time.", is_error=True)
            self.after(0, self.reset_ui_state)
            return
            
        # --- Build Command ---
        # yt-dlp's template processing will add the extension. We provide the path without it.
        output_template, _ = os.path.splitext(output_filename)
        ydl_opts = {
            'format': quality,
            'outtmpl': output_template,
            'quiet': True,
            'noplaylist': True,
            'progress_hooks': [self.update_progress],
            'logger': self.YTDLLogger(self),
        }

        # If ffmpeg is in the system path, self.ffmpeg_path is 'ffmpeg'.
        # In this case, we don't set ffmpeg_location and let yt-dlp find it.
        # Otherwise, self.ffmpeg_path is an absolute path to our local executable,
        # and we must specify its directory.
        if self.ffmpeg_path != 'ffmpeg':
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
        
        # Add download sections for clipping if a time range is specified
        if start_time_str or end_time_str:
            # yt-dlp expects a list of tuples for time ranges
            start_clip = start_seconds or 0
            end_clip = end_seconds or float('inf')
            download_ranges = yt_dlp.utils.download_range_func(None, [(start_clip, end_clip)])
            ydl_opts['download_ranges'] = download_ranges
            ydl_opts['force_keyframes_at_cuts'] = True

        # Recode if necessary
        is_audio_only = video_format in ['mp3', 'wav', 'aac']
        postprocessors = []
        if is_audio_only:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': video_format,
            })
        else:
            # For video, always recode to ensure the format is correct
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': video_format,
            })

        if self.gpu_codec and not is_audio_only:
            self.log_message(f"🚀 Using {self.gpu_vendor} GPU for faster processing.")
            ffmpeg_hw_args = []
            if sys.platform == 'win32':
                if self.gpu_vendor == 'NVIDIA':
                    ffmpeg_hw_args = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', '-c:v', self.gpu_codec]
                elif self.gpu_vendor in ('AMD', 'Intel'):
                    # Use D3D11VA for decode; encoders are AMF/QSV respectively
                    ffmpeg_hw_args = ['-hwaccel', 'd3d11va', '-c:v', self.gpu_codec]
                else:
                    ffmpeg_hw_args = ['-c:v', self.gpu_codec]
            elif sys.platform.startswith('linux'):
                if self.gpu_vendor == 'NVIDIA':
                    ffmpeg_hw_args = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda', '-c:v', self.gpu_codec]
                elif self.gpu_vendor in ('AMD', 'Intel'):
                    vaapi_device_path = self._find_vaapi_device()
                    if vaapi_device_path:
                        ffmpeg_hw_args = ['-vaapi_device', vaapi_device_path, '-vf', 'format=nv12,hwupload', '-c:v', self.gpu_codec]
                    else:
                        ffmpeg_hw_args = ['-c:v', self.gpu_codec]
                else:
                    ffmpeg_hw_args = ['-c:v', self.gpu_codec]
            else:
                # Fallback for other OSes
                ffmpeg_hw_args = ['-c:v', self.gpu_codec]

            ydl_opts.setdefault('postprocessor_args', {})
            ydl_opts['postprocessor_args']['FFmpegVideoConvertor'] = ffmpeg_hw_args

        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        # --- Execute Command ---
        self.log_message(f"▶️ Starting clip for: {url}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.log_message(f"✅ Success! Clip saved to: {output_filename}")
        except yt_dlp.utils.DownloadError as e:
            self.log_message(f"❌ Error during clipping process: {e}", is_error=True)
        except Exception as e:
            self.log_message(f"❌ An unexpected error occurred: {e}", is_error=True)
        finally:
            # Re-enable the button and hide progress bar on the main thread
            self.after(0, self.reset_ui_state)


if __name__ == "__main__":
    app = KayClipperApp()
    app.mainloop() 