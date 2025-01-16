# Harmonica - Discord Music Bot

Presenting "Harmonica" This self hosted bot uses YT-DLP to download audio files from YouTube, Spotify, direct links and livestream link sto play them directly in your Discord voice channel.

**NOTE: Currently it is considered Work In Progress, it has and will have bugs, but the general idea is there and it works.
Recommended to only use it on a SINGLE private Discord server, you have to self host it on either a VPS or on your own machine.**

Bot will misbehave if playing in multiple servers at the same time, this is a known issue and will be fixed in the future (However it is not a priority at the moment, you do not want your bot to be caught by the bigger fish).

Current Issues:
- [ ] Multiple servers does not work.

![Untitl11ed](https://github.com/user-attachments/assets/1ee417c8-db7c-458c-987d-95dcd909ee47)

## Setup

### Prerequisites
1. **Python**: Ensure you have Python 3.8 or higher installed.
2. **Dependencies**: Install the required Python packages using the following command:
   ```bash
   pip install -r requirements.txt
   ```

### Platform-Specific Instructions
- **Windows**: If `ffmpeg` is installed during the first initialization, you will need to relaunch the `bot.py` script.
- **macOS**: If `ffmpeg` fails to install automatically, manually place `ffmpeg` in the root directory.
- **Linux**: The setup script will automatically handle `ffmpeg` installation.
- **General**: yt-dlp and ffmpeg will be downloaded and set up automatically.

3. **Environment Variables**: Rename the `.env.example` file to `.env` and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_token_here
   ```
3.1 **[Optional]Spotify Credentials**: Rename the `.spotifyenv.example` file to `.spotifyenv` and add your Spotify credentials:
   ```
   SPOTIPY_CLIENT_ID=your_client_id_here
   SPOTIPY_CLIENT_SECRET=your_client_secret_here
   ```
   You can get these credentials by following the instructions in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).

3.2 **[Optional]Genius Credentials**: Edit the `.geniuslyrics` which gets created on first startup and add your Genius credentials:

4. **Cookies**: [Import cookies.txt](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) using the [Get Cookies.txt extension](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) and place it in the root directory. Skipping this step may limit the functionality of the bot.

5. **Run the Bot**: Start the bot using the following command:
   ```bash
   python bot.py
   ```

6. **Configure Configuration**: Edit the `config.json` file to configure the OWNER ID and PREFIX.

## Features
- **Play Music**: Stream music from YouTube directly into your Discord voice channel.
- **Playback Controls**: Basic controls like play, pause, skip, and stop.
- **Queue System**: Manage a queue of songs to play in sequence.
- **Loop Mode**: Toggle loop mode for continuous playback of the current song.
- **Optional Permissions**: DJ role can perform certain actions, such as skipping, clearing the queue.

## Commands
- `!help` - Display this help message.
- `!play [URL/search term]` - Play a song from YouTube or Spotify.
- `!search [search term]` - Searches the term on YouTube.
- `!join` - Join your voice channel. Aliases: `!summon`
- `!pause` - Pause the current song.
- `!resume` - Resume playback.
- `!stop` - Stop playback, clear the queue, and leave the voice channel.
- `!skip` - Skip the current song.
- `!clear` - Clear the queue. Aliases: `!clearqueue`
- `!clear [position]` - Remove song at specified position in queue.
- `!shuffle` - Shuffle the queue.
- `!queue` - Show the current song queue.
- `!replay` - Replays the current song.
- `!leave` - Leave the voice channel. Aliases: `!disconnect`
- `!loop` - Toggle loop mode for the current song. Aliases: `!repeat`
- `!loop [count]` - Toggle loop mode for the current song for the specified number of times. Aliases: `!repeat [count]`
- `!ping` - Show bot latency and connection info.
- `!log` - Log the current context.
- `!restart` - Restart the bot (Owner only).
- `!logclear` - Clear the log file (Owner only command).
- `!nowplaying` - Show the currently playing song.

## Troubleshooting
- **FFmpeg Installation**: Ensure `ffmpeg` is in your system's PATH. If issues persist, manually download and place `ffmpeg` in the bot's root directory.
- **Bot Token Issues**: Double-check that the Discord bot token is correctly placed in the `.env` file.
- **Please Sign-In YouTube Issue**: Your cookies.txt file may be either invalid, missing or expired. 

For further assistance, please refer to the bot's documentation or open a Issue on GitHub.
