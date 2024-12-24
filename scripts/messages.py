import discord
from discord.ext import commands

async def update_or_send_message(bot_instance, ctx, embed, view=None, force_new=False):
    """Update existing message or send a new one if none exists or if it's a new command"""
    try:
        if (force_new or 
            not bot_instance.current_command_msg or 
            ctx.author.id != bot_instance.current_command_author or 
            ctx.channel.id != bot_instance.current_command_msg.channel.id):
            
            bot_instance.current_command_msg = await ctx.send(embed=embed, view=view)
            bot_instance.current_command_author = ctx.author.id
        else:
            await bot_instance.current_command_msg.edit(embed=embed, view=view)
        
        return bot_instance.current_command_msg
    except Exception as e:
        print(f"Error updating message: {str(e)}")
        bot_instance.current_command_msg = await ctx.send(embed=embed, view=view)
        bot_instance.current_command_author = ctx.author.id
        return bot_instance.current_command_msg
