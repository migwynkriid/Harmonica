# Harmonica - Discord Music Bot 🎵

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.0+-blue.svg)](https://discordpy.readthedocs.io/en/stable/)
[![YT-DLP](https://img.shields.io/badge/YT--DLP-Latest-red.svg)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![SpotiPy](https://img.shields.io/badge/SpotiPy-2.23.0-brightgreen.svg)](https://spotipy.readthedocs.io/)

</div>

<div align="center">
  
<div style="border: 2px solid #5865F2; border-radius: 10px; padding: 20px; margin: 20px 0; background-color: #f6f8fa;">

# ⚙️ Public Harmonica Instance for your server

<a href="https://discord.com/oauth2/authorize?client_id=1341757638433833021&scope=bot+applications.commands">
  <img src="https://img.shields.io/badge/Invite%20Harmonica-Add%20to%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Invite Harmonica" width="300">
</a>


</div>

---

A self-hosted Discord bot that uses YT-DLP to play audio from YouTube, Spotify, direct links, and livestreams in your Discord voice channels.

![Bot Preview](https://github.com/user-attachments/assets/1ee417c8-db7c-458c-987d-95dcd909ee47)

## ✨ Features

### 🎵 Music Support
- Multi-platform support (YouTube, Spotify, direct links)
- Multi-server support
- High-quality audio streaming
- Livestream support
- Playlist support

### 📢 Sponsorblock
- Intergrated Sponsorblock
- Remove sponsor, intro, outro, selfpromo, interaction, and music offtopic from the audio
- Configurable via the config.json, by default it is disabled

### 🎚️ Playback Control
- Basic controls (play, pause, skip)
- Queue management
- Loop mode with count option
- Shuffle functionality
- Real-time track information

### 🎯 Smart Features
- ⚡ Advanced Caching System:
  - Automated local caching for faster playback
  - Skip YouTube queries for cached songs
  - Intelligent cache management
  - Reduced bandwidth usage
- YouTube search integration
- Spotify playlist parsing
- Genius lyrics integration
- Automatic FFmpeg setup
- Configurable auto-leave
- Download cleanup

### ⚙️ Administration
- Role-based permissions
- Configurable command prefix
- Detailed logging system
- Auto-updates capability

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
     - Sponsorblock

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

### Music Playback
- `!play [URL/search]` - Play audio from URL or search
- `!search [term]` - Search YouTube for a song
- `!pause` - Pause playback
- `!resume` - Resume playback
- `!stop` - Stop and clear queue
- `!skip` - Skip current track
- `!replay` - Replay current track
- `!random` - Searches for a random song on YouTube
- `!randomradio` - Play a random radio station
- `!loop [count]` - Toggle loop mode (optional count)
- `!nowplaying` - Show current track info

### Queue Management
- `!queue` - Show queue
- `!clear` - Clear entire queue
- `!clear [position]` - Remove specific track
- `!shuffle` - Shuffle queue

### Voice Channel
- `!join` / `!summon` - Join your channel
- `!leave` / `!disconnect` - Leave channel

### Lyrics & Information
- `!lyrics` - Get lyrics for current song

### System Commands
- `!alias [add/remove/list]` - Manage aliases
- `!ping` - Show bot status
- `!version` - Show bot version
- `!log` - Log current context
- `!restart` - Restart bot (Owner)
- `!logclear` - Clear logs (Owner)
- `!update` - Update bot files (Owner)
- `!help` - Show all commands

## 🔍 Troubleshooting

### Common Issues
- **FFmpeg Issues**: 
  - Windows: Relaunch after first install
  - macOS: Manual placement in root directory
  - Linux: Automatic installation

- **YouTube Sign-In Error/403 Error**: Check/update cookies.txt

## 📋 System Requirements
- Python 3.8+
- FFmpeg
- Stable internet connection
- Discord Bot Token
