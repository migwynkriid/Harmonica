import json
import subprocess

def get_audio_duration(file_path):
    """Get audio file duration using an optimized ffprobe command"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', file_path],
            capture_output=True,
            text=True
        )
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0
