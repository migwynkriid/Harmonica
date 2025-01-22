import discord
from discord.ext import commands
import psutil
import json
import os
from scripts.messages import create_embed
from scripts.permissions import check_dj_role

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
        self.bandwidth_file = 'bandwidth.json'
        self.current_bytes = psutil.net_io_counters()
        
        # Load or create bandwidth data
        if os.path.exists(self.bandwidth_file):
            with open(self.bandwidth_file, 'r') as f:
                self.bandwidth_data = json.load(f)
        else:
            self.bandwidth_data = {
                'total_bytes_sent': 0,
                'total_bytes_recv': 0,
                'last_bytes_sent': self.current_bytes.bytes_sent,
                'last_bytes_recv': self.current_bytes.bytes_recv
            }
            self._save_bandwidth_data()
    
    def _save_bandwidth_data(self):
        """Save bandwidth data to JSON file"""
        with open(self.bandwidth_file, 'w') as f:
            json.dump(self.bandwidth_data, f, indent=4)
    
    def _update_bandwidth_stats(self):
        """Update bandwidth statistics"""
        current_bytes = psutil.net_io_counters()
        
        # Calculate bytes since last update
        bytes_sent = current_bytes.bytes_sent - self.bandwidth_data['last_bytes_sent']
        bytes_recv = current_bytes.bytes_recv - self.bandwidth_data['last_bytes_recv']
        
        # Update total bytes
        self.bandwidth_data['total_bytes_sent'] += bytes_sent
        self.bandwidth_data['total_bytes_recv'] += bytes_recv
        
        # Update last bytes
        self.bandwidth_data['last_bytes_sent'] = current_bytes.bytes_sent
        self.bandwidth_data['last_bytes_recv'] = current_bytes.bytes_recv
        
        # Save updated data
        self._save_bandwidth_data()
        
        return self.bandwidth_data['total_bytes_sent'], self.bandwidth_data['total_bytes_recv']

    @commands.command(name='stats')
    @check_dj_role()
    async def stats(self, ctx):
        """Show bandwidth and system statistics"""
        try:
            # Update and get bandwidth stats
            bytes_sent, bytes_recv = self._update_bandwidth_stats()
            
            # Convert to more readable format
            def format_bytes(bytes_count):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if bytes_count < 1024:
                        return f"{bytes_count:.2f} {unit}"
                    bytes_count /= 1024
                return f"{bytes_count:.2f} TB"
            
            # Create embed with stats
            description = (
                f"**Total Network Usage:**\n"
                f"📤 Total Upload: {format_bytes(bytes_sent)}\n"
                f"📥 Total Download: {format_bytes(bytes_recv)}\n\n"
                f"**System Stats:**\n"
                f"💻 CPU Usage: {psutil.cpu_percent()}%\n"
                f"🧠 Memory Usage: {psutil.virtual_memory().percent}%"
            )
            
            await ctx.send(embed=create_embed("Bot Statistics", description, color=0x3498db, ctx=ctx))
            
        except Exception as e:
            await ctx.send(embed=create_embed("Error", f"Failed to get statistics: {str(e)}", color=0xe74c3c, ctx=ctx))

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
