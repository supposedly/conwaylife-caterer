import discord
import asyncio
import inspect
from discord.ext import commands
from cogs.resources import cmd
from platform import python_version

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self.invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
      # https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
    
    def to_command(self, arg):
        return self.bot.get_command(arg) if arg else None
    
    @commands.command(name='ping')
    async def ping(self, ctx):
        await ctx.send(f'Pong! That took {1000*self.bot.latency:.0f}ms.')
    
    @commands.command(name='link', aliases=cmd.aliases['link'], brief='Post an invite link for this bot')
    async def link(self, ctx):
        """# Produces an oauth2 invite link for this bot with necessary permissions. #"""
        em = discord.Embed(description=f'Use [this link]({self.invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @commands.command(name='help', aliases=cmd.aliases['help'], brief='Display this message')
    async def help(self, ctx, command=None):
        """
        # A prettified sort of help command — because regular HelpFormatter is for dweebs. #
        
        <[ARGS]>
        CMD: Command to display usage info for. If ommitted or invalid, displays generic help/info message.
        """
        command = self.bot.get_command(command) if command else None
        prefix = self.bot.command_prefix(self.bot, ctx.message)
        await ctx.channel.trigger_typing()
        if command is not None:
            msg = f'```nginx\n{prefix}{command.name} {cmd.args[command.name]}``````apache\n{command.help}```'
            if command.aliases:
                msg += '```apache\nAliases: {}```'.format(', '.join(prefix+i for i in command.aliases))
            await ctx.send(msg)
        else:
            center = max(map(len, (f'{prefix}{i.name: <5}| {i.brief}' for i in self.bot.commands)))
            desc = inspect.cleandoc(
            f"""
            **```ini
            {'[A cellular automata bot for Conwaylife.com]': ^{center}}```**```makefile
            Commands:
            """) + '\n'
            for com in (i for i in self.bot.commands if i.brief is not None):
                desc += f'{prefix}{com.name: <5}| {com.brief}\n'
            desc += '``````FORTRAN\n{1: ^{0}}\n{2: ^{0}}```'.format(center, f"'{prefix}help COMMAND' for command-specific docs", f"'{prefix}info' for credits & general information")
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)
    
    @commands.command(name='info', aliases=cmd.aliases['info'])
    async def info(self, ctx):
        """# Displays credits, useful links, and information about this bot's dependencies. #"""
        await ctx.send(embed=discord.Embed(description=f'''**```ini
{'[A cellular automata bot for Conwaylife.com]': ^57}```**
 **Version numbers:**
   python {python_version()}
   discord.py {discord.__version__} (rewrite)

 **Thanks to:**
   + Scorbie (GitHub contributor)
   + Conwaylife Lounge members (ideas & encouragement and stuff)
   + d-api and dpy servers (noob question support)
   + Hosted on Heroku

 **Links:**
   [GitHub repo](https://github.com/eltrhn/conwaylife-caterer)
   [Conwaylife.com forums](http://conwaylife.com/forums)
   [Support server/testnet](https://discord.gg/6A6hM72)

 **By Wright**
```FORTRAN
{f"'{self.bot.command_prefix(self.bot, ctx.message)}help' for command info": ^57}```'''))
    
def setup(bot):
    bot.add_cog(Utils(bot))
