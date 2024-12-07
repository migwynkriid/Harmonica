# Discord Music Bot

A Discord bot that plays music in voice channels.

## Setup
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt

   Also install yt-dlp.exe and ffmpeg.exe for Windows and place it in the root directory
   ```
3. Rename a `.env.example` file to `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Features
- Play music from YouTube
- Basic playback controls (play, pause, skip)
- Queue system for multiple songs

## Commands
- `!play [URL/search term]` - Play a song from YouTube
- `!pause` - Pause the current song
- `!resume` - Resume playback
- `!skip` - Skip the current song
- `!queue` - Show the current queue
- `!leave` - Leave the voice channel
