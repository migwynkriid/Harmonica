import discord
from discord.ui import Button, View
from scripts.config import load_config
from scripts.messages import create_embed
from datetime import datetime
from scripts.voice import leave_voice_channel

def should_show_buttons():
    """
    Check if UI buttons should be shown based on configuration.
    
    This function reads the bot configuration to determine whether
    interactive UI buttons should be displayed in Discord messages.
    The setting is controlled by the DISCORD_UI_BUTTONS parameter
    in the MESSAGES section of the config file.
    
    Returns:
        bool: True if buttons should be shown, False otherwise
    """
    config = load_config()
    messages = config.get('MESSAGES', config.get('messages', {}))
    return messages.get('DISCORD_UI_BUTTONS', messages.get('discord_ui_buttons', True))

def create_now_playing_view():
    """
    Create a new NowPlayingView if buttons are enabled, otherwise return None.
    
    This function serves as a factory for creating UI button views for
    the "now playing" messages. It checks if buttons are enabled in the
    configuration before creating a view to avoid unnecessary object creation.
    
    Returns:
        NowPlayingView or None: A new view instance if buttons are enabled, None otherwise
    """
    if should_show_buttons():
        return NowPlayingView()
    return None

class NowPlayingView(discord.ui.View):
    """
    Discord UI view for music player controls.
    
    This class implements an interactive UI with buttons for controlling
    music playback directly from Discord messages. It includes buttons for
    skipping songs, toggling loop mode, pausing/resuming playback, and
    stopping the bot.
    
    The view is persistent (no timeout) and includes permission checks
    to ensure only users in the same voice channel can use the controls.
    """
    def __init__(self):
        """Initialize the view with persistent timeout."""
        super().__init__(timeout=None)  # Make the view persistent

    def _create_embed_with_footer(self, title, description, color, thumbnail_url, interaction):
        """
        Create embed and add footer with user info.
        
        Helper method to create standardized embeds for button responses
        with consistent styling and user attribution in the footer.
        
        Args:
            title: The embed title
            description: The embed description
            color: The color of the embed
            thumbnail_url: Optional URL for the embed thumbnail
            interaction: The Discord interaction that triggered this response
            
        Returns:
            discord.Embed: The created embed with footer
        """
        embed = discord.Embed(
            title=title,
            description=description + "\n\u200b",
            color=color,
            timestamp=datetime.now()
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        return embed

    def _check_user_in_voice(self, interaction: discord.Interaction) -> bool:
        """
        Check if user is in the same voice channel as the bot.
        
        This method verifies that the user who clicked a button is in the
        same voice channel as the bot, preventing users from controlling
        playback from outside the channel.
        
        Args:
            interaction: The Discord interaction to check
            
        Returns:
            bool: True if the user is in the same voice channel as the bot, False otherwise
        """
        if not interaction.guild.voice_client:  # Bot not in any voice channel
            return False
        
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.voice:  # User not in any voice channel
            return False
            
        return member.voice.channel == interaction.guild.voice_client.channel

    @discord.ui.button(label="Next ⏭️", style=discord.ButtonStyle.primary, custom_id="skip_button", row=0)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Skip the current song.
        
        This button handler skips the currently playing song by calling
        the skip command functionality from the SkipCog. It includes
        permission checks and error handling.
        
        Args:
            interaction: The Discord interaction
            button: The button that was pressed
        """
        # Check if user is in the same voice channel
        if not self._check_user_in_voice(interaction):
            await interaction.response.defer()
            return
            
        skip_cog = interaction.client.get_cog('SkipCog')
        if skip_cog:
            success, result = await skip_cog._skip_song()
            # Acknowledge the button press without sending a visible response
            await interaction.response.defer()
            
            if not success:  # Only show message on error
                embed = self._create_embed_with_footer(
                    "Error",
                    result,
                    0xe74c3c,
                    None,
                    interaction
                )
                await interaction.channel.send(embed=embed)
        else:
            await interaction.response.defer()
            embed = self._create_embed_with_footer(
                "Error",
                "Skip functionality is not available",
                0xe74c3c,
                None,
                interaction
            )
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Loop 🔁", style=discord.ButtonStyle.secondary, custom_id="repeat_button", row=0)
    async def repeat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Toggle loop mode for the current song.
        
        This button handler toggles the loop mode by calling the loop
        command functionality from the Loop cog. The button changes color
        to indicate the current loop state.
        
        Args:
            interaction: The Discord interaction
            button: The button that was pressed
        """
        # Check if user is in the same voice channel
        if not self._check_user_in_voice(interaction):
            await interaction.response.defer()
            return
            
        loop_cog = interaction.client.get_cog('Loop')
        if loop_cog:
            success, result = await loop_cog._toggle_loop()
            # Acknowledge the button press without sending a visible response
            await interaction.response.defer()
            
            if success:
                if result['enabled']:
                    button.style = discord.ButtonStyle.success
                    title = "Looping enabled :repeat: "
                    color = 0x3498db
                else:
                    button.style = discord.ButtonStyle.secondary
                    title = "Looping disabled :repeat: "
                    color = 0xe74c3c

                embed = self._create_embed_with_footer(
                    title,
                    f"[{result['song']['title']}]({result['song']['url']})",
                    color,
                    result['song'].get('thumbnail'),
                    interaction
                )
                await interaction.channel.send(embed=embed)
            else:
                embed = self._create_embed_with_footer(
                    "Error",
                    result,
                    0xe74c3c,
                    None,
                    interaction
                )
                await interaction.channel.send(embed=embed)
        else:
            await interaction.response.defer()
            embed = self._create_embed_with_footer(
                "Error",
                "Loop functionality is not available",
                0xe74c3c,
                None,
                interaction
            )
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Pause ⏸️", style=discord.ButtonStyle.primary, custom_id="pause_resume_button", row=0)
    async def pause_resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Toggle between pause and resume states.
        
        This button handler toggles the playback state by pausing or resuming
        the music playback. It includes permission checks and error handling.
        
        Args:
            interaction: The Discord interaction
            button: The button that was pressed
        """
        # Check if user is in the same voice channel
        if not self._check_user_in_voice(interaction):
            await interaction.response.defer()
            return
            
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.defer()
            embed = self._create_embed_with_footer(
                "Error",
                "Not in a voice channel",
                0xe74c3c,
                None,
                interaction
            )
            await interaction.channel.send(embed=embed)
            return

        # Toggle between pause and resume
        try:
            # Get the current message embed
            message = interaction.message
            embed = message.embeds[0] if message.embeds else None
            
            if voice_client.is_paused():
                voice_client.resume()
                button.label = "Pause ⏸️"
                button.style = discord.ButtonStyle.primary
                # Remove "Paused" text if it exists
                if embed and embed.description:
                    embed.description = embed.description.replace("\n*Paused*", "")
            else:
                voice_client.pause()
                button.label = "Resume ▶️"
                button.style = discord.ButtonStyle.primary
                # Add "Paused" text if embed exists
                if embed and embed.description:
                    embed.description = f"{embed.description}\n*Paused*"

            # Update the message with modified embed and button
            await interaction.response.edit_message(embed=embed, view=self)

        except Exception as e:
            await interaction.response.defer()
            embed = self._create_embed_with_footer(
                "Error",
                f"Failed to toggle playback: {str(e)}",
                0xe74c3c,
                None,
                interaction
            )
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Stop ⛔", style=discord.ButtonStyle.danger, custom_id="stop_button", row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Stop playback and leave voice channel.
        
        This button handler stops the music playback and disconnects the
        bot from the voice channel. It includes permission checks and error
        handling.
        
        Args:
            interaction: The Discord interaction
            button: The button that was pressed
        """
        # Check if user is in the same voice channel
        if not self._check_user_in_voice(interaction):
            await interaction.response.defer()
            return
            
        # Acknowledge the button press without sending a visible response
        await interaction.response.defer()
        
        # Stop playback and leave voice channel
        if interaction.guild.voice_client:
            try:
                if interaction.guild.voice_client.is_playing():
                    interaction.guild.voice_client.stop()
                await interaction.guild.voice_client.disconnect(force=True)
                embed = self._create_embed_with_footer(
                    "Stopped",
                    "Music stopped and queue cleared",
                    0xe74c3c,
                    None,
                    interaction
                )
            except Exception as e:
                embed = self._create_embed_with_footer(
                    "Error",
                    f"Failed to leave voice channel: {str(e)}",
                    0xe74c3c,
                    None,
                    interaction
                )
            await interaction.channel.send(embed=embed)
        else:
            embed = self._create_embed_with_footer(
                "Error",
                "Not in a voice channel",
                0xe74c3c,
                None,
                interaction
            )
            await interaction.channel.send(embed=embed)
