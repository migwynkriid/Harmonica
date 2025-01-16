# Harmonica - Discord Music Bot 🎵

A self-hosted Discord bot that uses YT-DLP to play audio from YouTube, Spotify, direct links, and livestreams in your Discord voice channels.

![Bot Preview](https://github.com/user-attachments/assets/1ee417c8-db7c-458c-987d-95dcd909ee47)

> ⚠️ **Note**: This bot is currently in development. While functional, it's recommended for use on a single private Discord server only.

## ⚡ Quick Start

1. Install Python 3.8+
2. Run `pip install -r requirements.txt`
3. Rename `.env.example` to `.env` and add your Discord token
4. Run `python bot.py`

## 🔧 Detailed Setup

### Core Setup
1. **Python Installation**
   - Install Python 3.8 or higher
   - Verify installation: `python --version`

2. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Discord Bot Token**
   - Rename `.env.example` to `.env`
   - Add your token:
     ```
     DISCORD_TOKEN=your_token_here
     ```

4. **Configuration**
   - Edit `config.json` to set:
     - Owner ID
     - Command Prefix
     - Permissions
     - Autoleave
     - Default Volume
     - Auto Clear Downloads
     - Log Level
     - UI Buttons

### Optional Features

1. **Spotify Integration**
   - Rename `.spotifyenv.example` to `.spotifyenv`
   - Add credentials:
     ```
     SPOTIPY_CLIENT_ID=your_client_id_here
     SPOTIPY_CLIENT_SECRET=your_client_secret_here
     ```
   - Get credentials from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)

2. **Genius Lyrics**
   - Edit `.geniuslyrics` (created on first startup)
   - Add your [Genius API](https://genius.com/api-clients) credentials

3. **YouTube Authentication**
   - Install [Get Cookies.txt extension](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Export cookies and place in root directory
   - [Learn more about cookies setup](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)

## 🎮 Commands

### Playback Controls
- `!play [URL/search]` - Play audio from URL or search
- `!pause` - Pause playback
- `!resume` - Resume playback
- `!stop` - Stop and clear queue
- `!skip` - Skip current track
- `!replay` - Replay current track
- `!loop [count]` - Toggle loop mode (optional count)

### Queue Management
- `!queue` - Show queue
- `!clear` - Clear entire queue
- `!clear [position]` - Remove specific track
- `!shuffle` - Shuffle queue

### Voice Channel
- `!join` / `!summon` - Join your channel
- `!leave` / `!disconnect` - Leave channel

### System Commands
- `!ping` - Show bot status
- `!log` - Log current context
- `!restart` - Restart bot (Owner)
- `!logclear` - Clear logs (Owner)
- `!help` - Show all commands

## 🔍 Troubleshooting

### Common Issues
- **FFmpeg Issues**: 
  - Windows: Relaunch after first install
  - macOS: Manual placement in root directory
  - Linux: Automatic installation

- **YouTube Sign-In Error**: Check/update cookies.txt

- **Known Limitations**:
  - ❌ Multiple server support (WIP)

## 📋 System Requirements
- Python 3.8+
- FFmpeg
- Stable internet connection
- Discord Bot Token
