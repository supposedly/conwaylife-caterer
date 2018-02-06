import asyncio
import datetime as dt
import inspect
import pkg_resources
import platform

import asyncpg
import discord
from discord.ext import commands

from cogs.resources import utils

DISCORD_PUBLIC_VERSION = pkg_resources.get_distribution('discord.py').parsed_version.public
_lower = lambda x: x.lower()

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
      # https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
        self.bot.todos = None
    
    @staticmethod
    def lgst(dt_obj):
        """Returns a string representing the date in the largest applicable unit"""
        d = (dt.datetime.utcnow().date() - dt_obj).days
        return f'{d//365.25}y' if d >= 365.25 else f'{d//30}m' if d >= 30 else f'{d//7}w' if d >= 7 else f'{d}d'
        
    async def _set_todos(self):
        if self.bot.todos is None:
            async with self.pool.acquire() as conn:
                self.bot.todos = {
                  name: sorted([(i+1, self.lgst(v['date']), v['value']) for i, v in enumerate(await conn.fetch('''SELECT date, value FROM todo WHERE cmd = $1::text ORDER BY id''', name))], key=lambda x: x[0])
                  for name in {i['cmd'] for i in await conn.fetch('''SELECT DISTINCT cmd FROM todo ORDER BY cmd''')}
                  }
    
    @utils.group(name='todo', brief='List what Wright needs to implement')
    async def todo(self, ctx, *cmds: _lower):
        """
        # Shows an embedded list of features I plan to implement. #
        
        <[ARGS]>
        CMD: Command names (without any invocation prefix) to show todos for. If omitted, displays all todos, and if supplied but invalid, displays 'general' todos not tied to any one command.
        """
        desc = ''
        all_names = set(i.qualified_name for i in self.bot.walk_commands())
        await self._set_todos()
        desc = ( # FIXME: Why in the fresh hell did I one-line these
          ''.join(f'\n**{cmd[0]}{cmd[1]}**\n' + ''.join(f'  {val[0]}. ({val[1]}) {val[2].format(pre=ctx.prefix)}\n' for val in self.bot.todos[cmd[1]]) for cmd in {(ctx.prefix if cmd in all_names else '', cmd if cmd in all_names else 'general') for cmd in cmds})
        if cmds else
          ''.join(f'\n**{"" if key.lower() == "general" else ctx.prefix}{key}**\n' + ''.join(f'  {val[0]}. ({val[1]}) {val[2].format(pre=ctx.prefix)}\n' for val in ls) for key, ls in self.bot.todos.items())
        )
        await ctx.send(embed=discord.Embed(title='To-Dos', description=desc))
    
    @todo.command(name='add')
    @commands.is_owner()
    async def add_todo(self, ctx, cmd: _lower, *, value):
        if cmd not in (i.qualified_name.lower() for i in self.bot.walk_commands()):
            cmd = 'general'
        try:
            await self.pool.execute('''INSERT INTO todo (cmd, value, date) SELECT $1::text, $2::text, current_date''', cmd, value)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.todos = None # TODO: Maybe just append the newly-added todo with a calculated num 
            await ctx.message.add_reaction('👍')
    
    @todo.command(name='rm')
    @commands.is_owner()
    async def rm_todo(self, ctx, cmd: _lower, num: int):
        if cmd not in (i.qualified_name.lower() for i in self.bot.walk_commands()):
            cmd = 'general'
        await self._set_todos()
        for ls in self.bot.todos[cmd]:
            if ls[0] == num:
                value = ls[1]
                break
        else:
            return await ctx.message.add_reaction('👎')
        try:
            await self.pool.execute('''DELETE FROM todo WHERE cmd = $1::text AND value = $2::text''', cmd, value)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.todos = None # TODO: Maybe just pop the newly-removed todo and recalculate nums
            await ctx.message.add_reaction('👍')
    
    @utils.command(name='ping')
    async def ping(self, ctx):
        await ctx.send(f'Pong! That took {1000*self.bot.latency:.0f}ms.')
    
    @utils.command(name='link', brief='Post an invite link for this bot')
    async def link(self, ctx):
        """# Produces an oauth2 invite link for this bot with necessary permissions. #"""
        em = discord.Embed(description=f'Use [this link]({self.invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @utils.command(name='help', brief='Display this message')
    async def help(self, ctx, *, name=None):
        """
        # A prettified sort of help command — because HelpFormatter is for dweebs. #
        
        <[ARGS]>
        CMD: Command to display usage info for. If omitted or invalid, displays generic help/info message.
        ``````nginx
        Arguments will display in the topmost block of a "{prefix}help COMMAND" response with the following prefixes:
          ?: Optional argument.
          +: Infinitely-many distinct arguments, separated by spaces.
          *: Infinitely-many distinct arguments, allowing multi-word arguments if they are "quoted like this".
          >: Infinitely-long single argument. Quotation marks not required.
          -: A flag (optional). If the flag’s name is followed by a colon, it takes an argument (which will also be shown with the above prefixes).
        
        With the exception of the -hyphen prepended to a flag, these prefixes should NOT be written in the command invocation.
        In addition, a "/" symbol in the argument listing indicates that either (but not both) of the two arguments surrounding it will be accepted.
        """
        command = self.bot.get_command(name) if name else None
        await ctx.channel.trigger_typing()
        if command is not None:
            msg = f'```nginx\n{ctx.prefix}{command.helpsafe_name} {command.invocation_args}``````apache\n'
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
        desc = f'''**```ini
        {'[A cellular automata bot for Conwaylife.com]': ^57}```**
         **Version numbers:**
           python {platform.python_version()}
           discord.py {DISCORD_PUBLIC_VERSION} (rewrite)
        
         **Thanks to:**
           + Scorbie (GitHub contributor)
           + Conwaylife Lounge members (ideas & encouragement and stuff)
           + d-api and dpy servers (noob question support)
           + Hosted by Heroku
        
         **Links:**
           [GitHub repo](https://github.com/eltrhn/conwaylife-caterer)
           [Conwaylife.com forums](http://conwaylife.com/forums)
           [Support server/testnet](https://discord.gg/6A6hM72)
        
         **By Wright**
        ```FORTRAN
        {f"'{ctx.prefix}help' for command info": ^57}```
        '''
        await ctx.send(embed=discord.Embed(description=inspect.cleandoc(desc)))
    
def setup(bot):
    bot.add_cog(Utils(bot))
