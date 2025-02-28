import discord
from functools import wraps
from scripts.config import load_config
from scripts.messages import create_embed

def check_dj_role():
    """
    A decorator that checks if the user has the DJ role before executing the command.
    
    This decorator verifies whether the user has the 'DJ' role before allowing
    them to execute the decorated command. The check is only performed if
    REQUIRES_DJ_ROLE is set to true in the configuration. If the check fails,
    a permission denied message is sent to the channel.
    
    Returns:
        function: The decorator function that wraps the command
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            config = load_config()
            requires_dj = config.get('PERMISSIONS', {}).get('REQUIRES_DJ_ROLE', False)
            
            if not requires_dj:
                return await func(self, ctx, *args, **kwargs)
                
            # Check if user has DJ role
            dj_role = discord.utils.get(ctx.guild.roles, name='DJ')
            if dj_role and dj_role in ctx.author.roles:
                return await func(self, ctx, *args, **kwargs)
            else:
                embed = create_embed(
                    "Permission Denied",
                    "You need the 'DJ' role to use this command!",
                    color=0xe74c3c,
                    ctx=ctx
                )
                await ctx.send(embed=embed)
                return None
                
        return wrapper
    return decorator

def check_admin_role():
    """
    A decorator that checks if the user has the Administrator role before executing the command.
    
    This decorator verifies whether the user has the 'Administrator' role before
    allowing them to execute the decorated command. The check is only performed if
    REQUIRES_ADMIN_ROLE is set to true in the configuration. If the check fails,
    a permission denied message is sent to the channel.
    
    Returns:
        function: The decorator function that wraps the command
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx, *args, **kwargs):
            config = load_config()
            requires_admin = config.get('PERMISSIONS', {}).get('REQUIRES_ADMIN_ROLE', False)
            
            if not requires_admin:
                return await func(self, ctx, *args, **kwargs)
                
            # Check if user has Administrator role
            admin_role = discord.utils.get(ctx.guild.roles, name='Administrator')
            if admin_role and admin_role in ctx.author.roles:
                return await func(self, ctx, *args, **kwargs)
            else:
                embed = create_embed(
                    "Permission Denied",
                    "You need the 'Administrator' role to use this command!",
                    color=0xe74c3c,
                    ctx=ctx
                )
                await ctx.send(embed=embed)
                return None
                
        return wrapper
    return decorator
