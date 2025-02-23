import json
import asyncio
from typing import Optional

async def get_audio_duration(file_path) -> float:
    """Get audio file duration using an optimized ffprobe command asynchronously"""
    try:
        process = await asyncio.create_subprocess_exec(
            'ffprobe', '-v', 'error', 
            '-show_entries', 'format=duration',
            '-of', 'json', file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"Error getting audio duration: {stderr.decode()}")
            return 0.0
            
        data = json.loads(stdout.decode())
        duration = float(data['format']['duration'])
        return duration
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0.0
