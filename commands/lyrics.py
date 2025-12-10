from discord.ext import commands
import discord
import lyricsgenius
import os
from azapi import AZlyrics
from scripts.messages import create_embed

def create_token_file(filepath, token_prefix):
    """
    Helper function to create token files if they don't exist.
    
    Args:
        filepath (str): Path to the token file
        token_prefix (str): Prefix for the token in the file
        
    Returns:
        bool: True if file exists or was created successfully, False otherwise
    """
    if not os.path.exists(filepath):
        try:
            with open(filepath, 'w') as f:
                f.write(f'{token_prefix}=')
            return True
        except Exception:
            return False
    return True

def clean_song_title(title):
    """
    Remove text within brackets from song title.
    
    This function removes text within parentheses and square brackets
    to improve lyrics search accuracy.
    
    Args:
        title (str): The song title to clean
        
    Returns:
        str: The cleaned song title
    """
    import re
    # Remove text within parentheses () and square brackets []
    cleaned = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', title)
    # Remove extra whitespace and trim
    return ' '.join(cleaned.split())

def clean_lyrics(lyrics):
    """
    Remove text within brackets and unwanted lines from lyrics.
    
    This function cleans up lyrics by removing annotations, contributor
    information, and other non-lyric text.
    
    Args:
        lyrics (str): The raw lyrics text
        
    Returns:
        str: The cleaned lyrics
    """
    import re
    # Remove text within parentheses () and square brackets []
    cleaned = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', lyrics)
    # Remove extra whitespace and empty lines
    lines = [line.strip() for line in cleaned.split('\n')]
    # Filter out unwanted lines and empty lines
    filtered_lines = [
        line for line in lines 
        if line 
        and "You might also like" not in line
        and not re.match(r'^\d+ Contributors?$', line)  # Matches "X Contributors" where X is any number
    ]
    return '\n'.join(filtered_lines)

def split_into_chunks(text, max_size):
    """
    Split text into chunks without breaking words.
    
    This function splits a large text into smaller chunks that fit within
    Discord's message size limits, while preserving word boundaries.
    
    Args:
        text (str): The text to split
        max_size (int): Maximum size of each chunk in characters
        
    Returns:
        list: List of text chunks
    """
    # Split text into lines first to preserve line breaks
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        # If adding this line would exceed max_size
        if current_length + len(line) + 1 > max_size:  # +1 for newline
            # If current chunk has content, add it to chunks
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # If single line is longer than max_size, split it at word boundaries
            if len(line) > max_size:
                words = line.split()
                temp_line = []
                for word in words:
                    if current_length + len(' '.join(temp_line + [word])) <= max_size:
                        temp_line.append(word)
                        current_length = len(' '.join(temp_line))
                    else:
                        if temp_line:
                            current_chunk.append(' '.join(temp_line))
                            chunks.append('\n'.join(current_chunk))
                            current_chunk = []
                            temp_line = [word]
                            current_length = len(word)
                        else:
                            # Word itself is too long, split it (rare case)
                            chunks.append(word[:max_size])
                            word = word[max_size:]
                if temp_line:
                    current_chunk.append(' '.join(temp_line))
                    current_length = len(current_chunk[-1])
            else:
                current_chunk.append(line)
                current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline

    # Add any remaining content
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

async def setup(bot):
    """
    Setup function that runs when the extension is loaded.
    
    This function adds the lyrics command to the bot and ensures
    the necessary configuration files exist.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(lyrics)
    
    # Create .geniuslyrics file if it doesn't exist
    token_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.geniuslyrics')
    create_token_file(token_file, 'YOUR_GENIUS_CLIENT_ACCESS_TOKEN')
    
    return None

async def send_lyrics_embed(ctx, title, artist, lyrics, source=""):
    """
    Helper function to send lyrics in an embed.
    
    This function formats and sends the lyrics as a Discord embed,
    splitting them into chunks if necessary to fit within Discord's limits.
    
    Args:
        ctx: The command context
        title (str): The song title
        artist (str): The artist name
        lyrics (str): The song lyrics
        source (str): The source of the lyrics (e.g., "Genius", "AZLyrics")
    """
    # Clean the lyrics before displaying
    cleaned_lyrics = clean_lyrics(lyrics)
    
    embed = discord.Embed(
        title=f"Lyrics for: {title}",
        description=f"Artist: {artist}\nSource: {source}",
        color=0x3498db
    )
    
    # Use a slightly smaller chunk size to be safe
    chunk_size = 900  # Discord's field value limit is 1024, but we'll use less
    chunks = split_into_chunks(cleaned_lyrics, chunk_size)
    
    # Add chunks as separate fields
    for chunk in chunks:
        embed.add_field(
            name="\u200b",
            value=chunk,
            inline=False
        )
    
    await ctx.send(embed=embed)

@commands.command(name='lyrics')
async def lyrics(ctx):
    """
    Get lyrics for the currently playing song.
    
    This command attempts to find and display lyrics for the currently playing song.
    It first tries to use the Genius API if a token is available, then falls back
    to AZLyrics if Genius fails or no token is provided.
    
    Args:
        ctx: The command context
    """
    # Access the music_bot from the global scope
    from bot import MusicBot
    music_bot = MusicBot.get_instance(str(ctx.guild.id))

    # If MusicBot doesn't have a voice client but Discord does, try to sync them
    if not music_bot.voice_client and ctx.guild.voice_client:
        music_bot.voice_client = ctx.guild.voice_client
        
        # Try to find the correct instance if this one doesn't have current_song
        if not music_bot.current_song:
            for instance_id, instance in MusicBot._instances.items():
                if instance.current_song:
                    music_bot.current_song = instance.current_song
                    music_bot.is_playing = True
                    break
    
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
            api = AZlyrics('google', accuracy=0.1)
            
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
        api = AZlyrics('google', accuracy=0.1)
        
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
