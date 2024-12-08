# Discord Music Bot

Discord bot utilizing YT-DLP to download audio files of from YouTube and plays it locally  towards the voice channel.
## Setup
1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
Download `yt-dlp`, `ffmpeg`  and place it in the root directory where bot.py is placed in. <br> 
Optional: Do the same for `spot-dl`

3. Rename the `.env.example` file to `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```
4. Import cookies.txt using https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc and place it in the root directory

5. Run the bot:
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
