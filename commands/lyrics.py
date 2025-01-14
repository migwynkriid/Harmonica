from discord.ext import commands
import discord
import lyricsgenius
import os
import sys
from azapi import AZlyrics
from scripts.messages import create_embed

# Add the parent directory to sys.path to allow importing from bot
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

def create_token_file(filepath, token_prefix):
    """Helper function to create token files if they don't exist"""
    if not os.path.exists(filepath):
        try:
            with open(filepath, 'w') as f:
                f.write(f'{token_prefix}=')
            return True
        except Exception:
            return False
    return True

def clean_song_title(title):
    """Remove text within brackets from song title"""
    import re
    # Remove text within parentheses () and square brackets []
    cleaned = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)
    # Remove extra whitespace and trim
    return ' '.join(cleaned.split())

async def setup(bot):
    """Setup function that runs when the extension is loaded"""
    bot.add_command(lyrics)
    
    # Create .geniuslyrics file if it doesn't exist
    token_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.geniuslyrics')
    create_token_file(token_file, 'YOUR_GENIUS_CLIENT_ACCESS_TOKEN')
    
    return None

async def send_lyrics_embed(ctx, title, artist, lyrics, source=""):
    """Helper function to send lyrics in an embed"""
    embed = discord.Embed(
        title=f"Lyrics for: {title}",
        description=f"Artist: {artist}\nSource: {source}",
        color=0x3498db
    )
    
    # Split lyrics into chunks (Discord has a 4096 character limit for embed fields)
    chunk_size = 1024  # Discord's field value limit
    chunks = [lyrics[i:i + chunk_size] for i in range(0, len(lyrics), chunk_size)]
    
    # Add chunks as separate fields
    for i, chunk in enumerate(chunks, 1):
        embed.add_field(
            name=f"Part {i}" if i > 1 else "\u200b",
            value=chunk,
            inline=False
        )
    
    await ctx.send(embed=embed)

@commands.command(name='lyrics')
async def lyrics(ctx):
    """Get lyrics for the current song"""
    # Access the music_bot from the global scope
    from bot import music_bot
    
    if not music_bot:
        await ctx.send(embed=create_embed("Error", "Music bot is not initialized yet. Please wait a moment and try again.", color=0xe74c3c, ctx=ctx))
        return

    if not music_bot.current_song:
        await ctx.send(embed=create_embed("Error", "No song is currently playing!", color=0xe74c3c, ctx=ctx))
        return
        
    # Get current song title and clean it
    query = music_bot.current_song.get('title')
    if not query:
        await ctx.send(embed=create_embed("Error", "Could not get the current song's title.", color=0xe74c3c, ctx=ctx))
        return
    
    # Clean the song title before searching
    cleaned_query = clean_song_title(query)

    # Get token from .geniuslyrics file
    token_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.geniuslyrics')
    try:
        with open(token_file, 'r') as f:
            content = f.read().strip()
            if not content.startswith('YOUR_GENIUS_CLIENT_ACCESS_TOKEN='):
                with open(token_file, 'w') as f:
                    f.write('YOUR_GENIUS_CLIENT_ACCESS_TOKEN=')
                await ctx.send(embed=create_embed("Configuration Error", "Invalid token format. The `.geniuslyrics` file has been reset. Please add your token after 'YOUR_GENIUS_CLIENT_ACCESS_TOKEN='", color=0xe74c3c, ctx=ctx))
                return
            genius_token = content.split('YOUR_GENIUS_CLIENT_ACCESS_TOKEN=', 1)[1].strip()
    except FileNotFoundError:
        # Try to create the file if it doesn't exist
        try:
            create_token_file(token_file, 'YOUR_GENIUS_CLIENT_ACCESS_TOKEN')
            await ctx.send(embed=create_embed("Configuration", "Created `.geniuslyrics` file. Please add your Genius API token after 'YOUR_GENIUS_CLIENT_ACCESS_TOKEN='", color=0x3498db, ctx=ctx))
        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"Error creating `.geniuslyrics` file: {str(e)}", color=0xe74c3c, ctx=ctx))
        return
    except Exception as e:
        await ctx.send(embed=create_embed("Error", f"Error reading Genius API token: {str(e)}", color=0xe74c3c, ctx=ctx))
        return
    
    if not genius_token:
        # Skip Genius and try AZLyrics directly
        try:
            # Initialize AZLyrics
            api = AZlyrics()
            
            # Try to split the title which is usually in "Artist - Song" format
            if " - " in cleaned_query:
                artist, title = cleaned_query.split(" - ", 1)
            else:
                # If no clear separator, use the whole title as song name
                title = cleaned_query
                artist = ""
            
            # Search for lyrics
            api.title = title
            api.artist = artist
            lyrics = api.getLyrics(save=False)
            
            if lyrics and lyrics != "":
                await send_lyrics_embed(ctx, query, artist if artist else "Unknown Artist", lyrics, "AZLyrics")
                return
            
            await ctx.send(embed=create_embed("Not Found", f"Could not find lyrics for: {query}", color=0xe74c3c, ctx=ctx))
            return
                
        except Exception as e:
            await ctx.send(embed=create_embed("Not Found", f"Could not find lyrics for: {query}", color=0xe74c3c, ctx=ctx))
            return
    
    try:
        # First try with Genius
        genius = lyricsgenius.Genius(genius_token)
        song = genius.search_song(cleaned_query)
        
        if song:
            await send_lyrics_embed(ctx, song.title, song.artist, song.lyrics, "Genius")
            return
            
    except Exception as e:
        if "403" in str(e):
            pass  # Skip to AZLyrics fallback
        else:
            await ctx.send(embed=create_embed("Error", f"An error occurred while fetching lyrics: {str(e)}", color=0xe74c3c, ctx=ctx))
            return
            
    # If Genius fails, try with AZLyrics
    try:
        # Initialize AZLyrics
        api = AZlyrics()
        
        # Try to split the title which is usually in "Artist - Song" format
        if " - " in cleaned_query:
            artist, title = cleaned_query.split(" - ", 1)
        else:
            # If no clear separator, use the whole title as song name
            title = cleaned_query
            artist = ""
        
        # Search for lyrics
        api.title = title
        api.artist = artist
        lyrics = api.getLyrics(save=False)
        
        if lyrics and lyrics != "":
            await send_lyrics_embed(ctx, query, artist if artist else "Unknown Artist", lyrics, "AZLyrics")
            return
        
        await ctx.send(embed=create_embed("Not Found", f"Could not find lyrics for: {cleaned_query}", color=0xe74c3c, ctx=ctx))
            
    except Exception as e:
        await ctx.send(embed=create_embed("Not Found", f"Could not find lyrics for: {cleaned_query}", color=0xe74c3c, ctx=ctx))
