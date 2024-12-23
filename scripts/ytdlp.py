import os
import sys
import urllib.request
import platform

def ensure_ytdlp():
    try:
        if sys.platform.startswith('win'):
            ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yt-dlp.exe')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp for Windows...")
                url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp.exe"
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)
                print("yt-dlp.exe downloaded successfully")
            return ytdlp_path
        elif sys.platform.startswith('darwin'):
            ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yt-dlp')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp for macOS...")
                url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_macos"
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)
                print("yt-dlp downloaded successfully")
            return ytdlp_path
        else:
            ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'yt-dlp')
            if not os.path.exists(ytdlp_path):
                print("Downloading yt-dlp for Linux...")   
                machine = platform.machine().lower()
                if machine in ['aarch64', 'arm64']:
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux_aarch64"
                elif machine == 'armv7l':
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux_armv7l"
                else:
                    url = "https://github.com/yt-dlp/yt-dlp-nightly-builds/releases/latest/download/yt-dlp_linux"
                print(f"Detected architecture: {machine}, downloading appropriate version...")
                urllib.request.urlretrieve(url, ytdlp_path)
                os.chmod(ytdlp_path, 0o755)
                print("yt-dlp downloaded successfully")
            return ytdlp_path
    except Exception as e:
        print(f"Error downloading yt-dlp: {str(e)}")
        return None

def get_ytdlp_path():
    local_path = os.path.join(os.getcwd(), 'yt-dlp')
    if os.path.exists(local_path):
        return local_path
    return 'yt-dlp'
