import discord
from discord.ext import commands
import subprocess
import asyncio
from scripts.messages import create_embed
from scripts.constants import EMBED_COLOR_ERROR, EMBED_COLOR_SUCCESS, EMBED_COLOR_INFO

# Number emoji reactions for selection (1-9)
NUMBER_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']


async def setup(bot):
    """
    Setup function to add the branch command to the bot.
    
    Args:
        bot: The bot instance
    """
    bot.add_command(branch)
    return None


def get_branches():
    """
    Get all local and remote branches.
    
    Returns:
        tuple: (current_branch, local_branches, remote_branches)
    """
    try:
        # Get current branch
        current = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        
        # Get local branches
        local_output = subprocess.run(
            ["git", "branch"],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        
        local_branches = []
        for line in local_output.split('\n'):
            branch = line.strip().lstrip('* ').strip()
            if branch:
                local_branches.append(branch)
        
        # Fetch remote to get latest branches
        try:
            subprocess.run(["git", "fetch", "--prune"], capture_output=True, text=True)
        except:
            pass  # Ignore fetch errors
        
        # Get remote branches
        remote_output = subprocess.run(
            ["git", "branch", "-r"],
            check=True, capture_output=True, text=True
        ).stdout.strip()
        
        remote_branches = []
        for line in remote_output.split('\n'):
            branch = line.strip()
            if branch and 'HEAD' not in branch:
                # Remove 'origin/' prefix for display but keep track
                clean_name = branch.replace('origin/', '')
                if clean_name not in local_branches:
                    remote_branches.append(clean_name)
        
        return current, local_branches, remote_branches
        
    except subprocess.CalledProcessError:
        return None, [], []
    except FileNotFoundError:
        return None, [], []


def switch_branch(branch_name, is_remote=False):
    """
    Switch to a different branch.
    
    Args:
        branch_name: Name of the branch to switch to
        is_remote: Whether this is a remote-only branch
        
    Returns:
        tuple: (success, message)
    """
    try:
        if is_remote:
            # Checkout remote branch and create local tracking branch
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name, f"origin/{branch_name}"],
                check=True, capture_output=True, text=True
            )
        else:
            # Switch to existing local branch
            result = subprocess.run(
                ["git", "checkout", branch_name],
                check=True, capture_output=True, text=True
            )
        return True, f"Switched to branch `{branch_name}`"
    except subprocess.CalledProcessError as e:
        # If branch already exists locally when trying to checkout remote
        if "already exists" in e.stderr:
            try:
                subprocess.run(
                    ["git", "checkout", branch_name],
                    check=True, capture_output=True, text=True
                )
                return True, f"Switched to branch `{branch_name}`"
            except subprocess.CalledProcessError as e2:
                return False, f"Failed to switch: {e2.stderr}"
        return False, f"Failed to switch: {e.stderr}"


@commands.command(name='branch')
@commands.is_owner()
async def branch(ctx):
    """
    List and switch between git branches.
    
    This command shows all local and remote branches, allowing the bot owner
    to switch branches by reacting with the corresponding number.
    
    This command is restricted to the bot owner only.
    
    Args:
        ctx: The command context
    """
    # Get branches
    current, local_branches, remote_branches = get_branches()
    
    if current is None:
        embed = create_embed(
            "Error",
            "Not a git repository or git is not installed.",
            color=EMBED_COLOR_ERROR,
            ctx=ctx
        )
        await ctx.send(embed=embed)
        return
    
    if not local_branches and not remote_branches:
        embed = create_embed(
            "Error",
            "No branches found.",
            color=EMBED_COLOR_ERROR,
            ctx=ctx
        )
        await ctx.send(embed=embed)
        return
    
    # Build branch list for selection
    all_branches = []
    description_lines = [f"**Current branch:** `{current}`\n"]
    
    # Add local branches
    if local_branches:
        description_lines.append("**Local Branches:**")
        for branch_name in local_branches:
            if len(all_branches) >= 9:  # Max 9 options
                break
            idx = len(all_branches)
            marker = " ← current" if branch_name == current else ""
            description_lines.append(f"{NUMBER_EMOJIS[idx]} `{branch_name}`{marker}")
            all_branches.append(('local', branch_name))
    
    # Add remote-only branches
    if remote_branches and len(all_branches) < 9:
        description_lines.append("\n**Remote Branches (not checked out locally):**")
        for branch_name in remote_branches:
            if len(all_branches) >= 9:  # Max 9 options
                break
            idx = len(all_branches)
            description_lines.append(f"{NUMBER_EMOJIS[idx]} `{branch_name}` (remote)")
            all_branches.append(('remote', branch_name))
    
    description_lines.append("\n*React with a number to switch branches, or ❌ to cancel.*")
    
    embed = create_embed(
        "Git Branches",
        "\n".join(description_lines),
        color=EMBED_COLOR_INFO,
        ctx=ctx
    )
    
    msg = await ctx.send(embed=embed)
    
    # Add reactions
    for i in range(len(all_branches)):
        await msg.add_reaction(NUMBER_EMOJIS[i])
    await msg.add_reaction('❌')
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            reaction.message.id == msg.id and 
            (str(reaction.emoji) in NUMBER_EMOJIS[:len(all_branches)] or str(reaction.emoji) == '❌')
        )
    
    try:
        reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if str(reaction.emoji) == '❌':
            await msg.edit(embed=create_embed(
                "Cancelled",
                "Branch switch cancelled.",
                color=EMBED_COLOR_INFO,
                ctx=ctx
            ))
            await msg.clear_reactions()
            return
        
        # Get selected branch
        idx = NUMBER_EMOJIS.index(str(reaction.emoji))
        branch_type, branch_name = all_branches[idx]
        
        if branch_name == current:
            await msg.edit(embed=create_embed(
                "Already on this branch",
                f"You're already on `{branch_name}`.",
                color=EMBED_COLOR_INFO,
                ctx=ctx
            ))
            await msg.clear_reactions()
            return
        
        # Switch branch
        await msg.edit(embed=create_embed(
            "Switching...",
            f"Switching to `{branch_name}`...",
            color=EMBED_COLOR_INFO,
            ctx=ctx
        ))
        await msg.clear_reactions()
        
        success, message = switch_branch(branch_name, is_remote=(branch_type == 'remote'))
        
        if success:
            embed = create_embed(
                "Branch Switched",
                f"{message}\n\n⚠️ **Restart the bot to apply changes from the new branch.**",
                color=EMBED_COLOR_SUCCESS,
                ctx=ctx
            )
        else:
            embed = create_embed(
                "Error",
                message,
                color=EMBED_COLOR_ERROR,
                ctx=ctx
            )
        
        await msg.edit(embed=embed)
        
    except asyncio.TimeoutError:
        await msg.edit(embed=create_embed(
            "Timeout",
            "Branch selection timed out.",
            color=EMBED_COLOR_ERROR,
            ctx=ctx
        ))
        await msg.clear_reactions()
