import asyncio
import inspect
from platform import python_version

import discord
from discord.ext import commands

from cogs.resources import utils, cmd

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self.invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
      # https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
    
    def to_command(self, arg):
        return self.bot.get_command(arg) if arg else None
    
    @utils.command('ping')
    async def ping(self, ctx):
        await ctx.send(f'Pong! That took {1000*self.bot.latency:.0f}ms.')
    
    @utils.command('link', brief='Post an invite link for this bot')
    async def link(self, ctx):
        """# Produces an oauth2 invite link for this bot with necessary permissions. #"""
        em = discord.Embed(description=f'Use [this link]({self.invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @utils.command('help', brief='Display this message')
    async def help(self, ctx, *, name=None):
        """
        # A prettified sort of help command — because HelpFormatter is for dweebs. #
        
        <[ARGS]>
        CMD: Command to display usage info for. If ommitted or invalid, displays generic help/info message.
        ``````nginx
        Arguments will display in the topmost block of a "{prefix}help COMMAND" response with the following prefixes:
          ?: Optional argument.
          +: Infinitely-many distinct arguments, separated by spaces.
          *: Infinitely-many arguments, allowing multi-word arguments if they are "quoted like this".
          >: Infinitely-long single argument. Quotation marks not required.
          -: A flag (optional). If the flag’s name is followed by a colon, it takes an argument (which will also be shown with the above prefixes).
        
        With the exception of the -hyphen prepended to a flag, these prefixes should NOT be written in the command invocation.
        In addition, a "/" symbol in the argument listing indicates that either (but not both) of the two arguments surrounding it will be accepted.
        """
        command = self.bot.get_command(name) if name else None
        await ctx.channel.trigger_typing()
        if command is not None:
            msg = f'```nginx\n{ctx.prefix}{command.qualified_name.replace(" ", "/")} {cmd.args.get(command.qualified_name, "")}``````apache\n'
            if isinstance(command, commands.GroupMixin):
                msg += 'Subcommands: {}``````apache\n'.format(', '.join(i.name for i in set(command.walk_commands())))
            msg += command.help.format(prefix=ctx.prefix, inherits=f'[See {ctx.prefix}help {getattr(command, "parent", "")}]') + '```'
            if command.aliases:
                prep = ctx.prefix if command.parent is None else f'{ctx.prefix}{command.full_parent_name} '
                msg += '```apache\nAliases: {}```'.format(', '.join(map(prep.__add__, command.aliases)))
            await ctx.send(msg)
        else:
            center = max(map(len, (f'{ctx.prefix}{i.name: <5}| {i.brief}' for i in self.bot.commands)))
            desc = inspect.cleandoc(
              f"""
              **```ini
              {'[A cellular automata bot for Conwaylife.com]': ^{center}}```**```makefile
              Commands:
              """
            ) + '\n'
            for com in (i for i in self.bot.commands if i.brief is not None):
                desc += f'{ctx.prefix}{com.name: <5}| {com.brief}\n'
            desc += '``````FORTRAN\n{1: ^{0}}\n{2: ^{0}}```'.format(center, f"'{ctx.prefix}help COMMAND' for command-specific docs", f"'{ctx.prefix}info' for credits & general information")
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)
    
    @utils.command(name='info')
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
{f"'{ctx.prefix}help' for command info": ^57}```'''))
    
def setup(bot):
    bot.add_cog(Utils(bot))
