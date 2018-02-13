import asyncio
import inspect
import itertools
import pkg_resources
import platform
import datetime as dt

import asyncpg
import discord
from discord.ext import commands

from cogs.resources import mutils

DISCORD_PUBLIC_VERSION = pkg_resources.get_distribution('discord.py').parsed_version.public

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
      # https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
        self.bot.changelog = self.bot.changelog_last_updated = self.bot.todos = None
    
    @staticmethod
    def lgst(dt_obj):
        """Return a string abbreviating given date to the largest appropriate unit"""
        d = (dt.datetime.utcnow().date() - dt_obj).days
        return f'{d//365.25}y' if d >= 365 else f'{d//30}m' if d >= 30 else f'{d//7}w' if d >= 7 else f'{d}d'
    
    async def _set_todos(self):
        if self.bot.todos is None:
            async with self.pool.acquire() as conn:
                self.bot.todos = {
                  cmd: [(i, v['date'], v['value']) for i, v in enumerate(await conn.fetch('''SELECT date, value FROM todo WHERE cmd = $1::text ORDER BY id''', cmd), 1)]
                  for cmd in {j['cmd'] for j in await conn.fetch('''SELECT DISTINCT cmd FROM todo ORDER BY cmd''')}
                  }
    
    async def _set_changelog(self):
        if self.bot.changelog is None:
            async with self.pool.acquire() as conn:
                # Delete old entries first
                await conn.execute('''DELETE FROM changes WHERE (current_date - changes.date) > 30''')
                # Then set changelog in order of date -> command -> days in progress: todo text
                self.bot.changelog = {
                  date: {
                    cmd: [(i['date_created'], i['value']) for i in await conn.fetch('''SELECT date_created, value FROM changes WHERE cmd = $1::text ORDER BY date_created DESC''', cmd)]
                    for cmd in {j['cmd'] for j in await conn.fetch('''SELECT DISTINCT cmd FROM changes WHERE date = $1::date ORDER BY cmd''', date)}
                    }
                  for date in {k['date'] for k in await conn.fetch('''SELECT DISTINCT date FROM changes ORDER BY date DESC''')} # desc puts 'larger', aka more recent, dates first
                  }

    async def _find_todo(self, cmd, num):
        await self._set_todos()
        if cmd not in {i.qualified_name.lower() for i in self.bot.walk_commands()}:
            cmd = 'general'
        for idx, _, value in self.bot.todos[cmd]:
            if idx == num:
                break
        else:
            return None
        return cmd, value
    
    @mutils.group(brief='List what Wright needs to implement')
    async def todo(self, ctx, *cmds: str.lower):
        """
        # Shows an embedded list of features I plan to implement. #
        
        <[ARGS]>
        CMD: Command names (without any invocation prefix) to show todos for. If omitted, displays all todos, and if supplied but invalid, displays 'general' todos not tied to any one command.
        """
        desc = ''
        all_names = set(i.qualified_name for i in self.bot.walk_commands())
        await self._set_todos()
        desc = ''.join(
          (
            f'\n**{pre}{cmd}**\n'
            + ''.join(
              f'  {idx}. ({self.lgst(date)}) {(val[0].upper()+val[1:]).format(pre=ctx.prefix)}\n'
            for idx, date, val in self.bot.todos[cmd]
            )
          for pre, cmd in {(ctx.prefix if name in all_names else '', name if name in all_names else 'general') for name in cmds}
          )
          if cmds else
          (
            f'\n**{"" if cmd.lower() == "general" else ctx.prefix}{cmd}**\n'
            + ''.join(
              f'  {idx}. ({self.lgst(date)}) {(val[0].upper()+val[1:]).format(pre=ctx.prefix)}\n'
            for idx, date, val in ls
            )
          for cmd, ls in self.bot.todos.items()
          )
        )
        await ctx.send(embed=discord.Embed(title='To-Dos', description=desc))
    
    @todo.command('add')
    @commands.is_owner()
    async def add_todo(self, ctx, cmd: str.lower, *, value):
        if cmd not in {i.qualified_name.lower() for i in self.bot.walk_commands()}:
            cmd = 'general'
        try:
            await self.pool.execute('''INSERT INTO todo (cmd, value, date) SELECT $1::text, $2::text, current_date''', cmd, value)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.todos = None # TODO: Maybe just append the newly-added todo with a calculated num 
            await ctx.thumbsup()
    
    @todo.command('del')
    @commands.is_owner()
    async def guillermo_del_todo(self, ctx, cmd: str.lower, num: int):
        try:
            cmd, value = await self._find_todo(cmd, num)
        except TypeError:
            return await ctx.thumbsdown()
        try:
            await self.pool.execute('''DELETE FROM todo WHERE value = $2::text AND cmd = $1::text''', cmd, value)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.todos = None # TODO: Maybe just pop the newly-removed todo and recalculate nums
            await ctx.thumbsup()
    
    @todo.command('complete')
    @commands.is_owner()
    async def finish_todo(self, ctx, cmd: str.lower, num: int, *flags):
        flags = mutils.parse_flags(flags)
        try:
            cmd, value = await self._find_todo(cmd, num)
        except TypeError:
            return await ctx.thumbsdown()
        pre = f'{flags["pre"]} ' if 'pre' in flags else ''
        note = f'{flags["note"]} ' if 'note' in flags else ''
        try:
            await self.pool.execute('''
            INSERT INTO changes
              (cmd, value, date, date_created)
            SELECT
              $1::text,
              $3::text,
              current_date,
              todo.date
            FROM todo
            WHERE todo.cmd = $1::text AND todo.value = $2::text''', cmd, value, pre+value+note)
            await self.pool.execute('''DELETE FROM todo WHERE value = $2::text AND cmd = $1::text''', cmd, value)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.changelog_last_updated = dt.date.today()
            self.bot.changelog = None # TODO: Maybe (???) just append the new change
            self.bot.todos = None
            await ctx.thumbsup()
    
    @todo.command('move')
    @commands.is_owner()
    async def move_todo(self, ctx, old: str.lower, num: int, new: str.lower):
        try:
            old, value = await self._find_todo(old, num)
        except TypeError:
            return await ctx.thumbsdown()
        if new not in {i.qualified_name.lower() for i in self.bot.walk_commands()}:
            new = 'general'
        try:
            await self.pool.execute('''UPDATE todo SET cmd = $3::text WHERE value = $2::text AND cmd = $1::text''', old, value, new)
        except Exception as e:
            await ctx.send(f'`{e.__class__.__name__}: {e}`')
        else:
            self.bot.todos = None # TODO: Maybe just pop the newly-removed todo and recalculate nums
            await ctx.thumbsup()
    
    @mutils.command(brief='Show a 30-day changelog')
    async def new(self, ctx):
        desc = ''
        await self._set_changelog()
        desc = '\n'.join(
          f'__{date}__\n'
          + '\n'.join(
            f'  **{"" if cmd.lower() == "general" else ctx.prefix}{cmd}**\n'
            + ''.join(
              f'    ({self.lgst(date_created)}) {(val[0].upper()+val[1:]).format(pre=ctx.prefix)}\n'
            for date_created, val in ls
            )
          for cmd, ls in cmd_data.items()
          )
        for date, cmd_data in self.bot.changelog.items()
        )
        em = discord.Embed(title='Changelog', description=desc)
        em.set_footer(text=f'Last updated: {self.bot.changelog_last_updated or "Not since bot was last restarted"}')
        await ctx.send(embed=em)
    
    @mutils.command()
    async def ping(self, ctx):
        resp = await ctx.send(f'Pong! Loading...')
        diff = resp.created_at - ctx.message.created_at
        await resp.edit(content=f'Pong! That took {1000*diff.total_seconds():.1f}ms.\n(Discord websocket latency: {1000*self.bot.latency:.1f}ms)')
    
    @mutils.command(brief='Post an invite link for this bot')
    async def link(self, ctx):
        """# Procures an oauth2 invite link for this bot with necessary permissions. #"""
        em = discord.Embed(description=f'Use [this link]({self.invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @mutils.command(brief='Display this message')
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
            # FIXME: Spacing below is hardcoded when it should be a function of the longest command name
            center = max(map(len, (f'{ctx.prefix}{i.name: <{self.bot.help_padding}}| {i.brief}' for i in self.bot.commands)))
            desc = inspect.cleandoc(
              f"""
              **```ini
              {'[A cellular automata bot for Conwaylife.com]': ^{center}}```**```makefile
              Commands:
              """
              ) + '\n'
            desc += ''.join(f'{ctx.prefix}{cmd.name: <{self.bot.help_padding}}| {cmd.brief}\n' for cmd in self.bot.sorted_commands if cmd.brief is not None)
            desc += '``````FORTRAN\n{1: ^{0}}\n{2: ^{0}}```'.format(center, f"'{ctx.prefix}help COMMAND' for command-specific docs", f"'{ctx.prefix}info' for credits & general information")
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)
    
    @mutils.command()
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
    
    @mutils.command()
    async def logs(self, ctx, start=0):
        """# Displays recent logs for debugging #"""
        start = max(0, min(len(self.bot.logs)-20, start))
        log = await ctx.send(
          f'**{len(self.bot.logs)-start-20}..{len(self.bot.logs)-start} of {len(self.bot.logs)} log entries**\n'
          '```css\n'
          + ''.join(reversed(list((itertools.islice(self.bot.logs, start, 20+start)))))
          + '```'
        )
        while True:
            available = '⬆⬇'[start >= len(self.bot.logs)-20 : 1 + bool(start)]
            [await log.add_reaction(i) for i in available]
            try:
                rxn, usr = await self.bot.wait_for(
                  'reaction_add',
                  timeout = 30.0,
                  check = lambda rxn, usr: all((rxn.emoji in available, usr is ctx.message.author, rxn.message.id == log.id))
                  )
            except asyncio.TimeoutError:
                return await log.clear_reactions()
            await log.clear_reactions()
            start = max(0, min(len(self.bot.logs)-20, start + 10*((rxn.emoji == '⬆') - (rxn.emoji == '⬇'))))
            await log.edit(content =
              f'**{len(self.bot.logs)-start-20}..{len(self.bot.logs)-start} of {len(self.bot.logs)} log entries**\n'
              '```css\n'
              + ''.join(reversed(list(itertools.islice(self.bot.logs, start, 20+start))))
              + '```'
            )
            


def setup(bot):
    bot.add_cog(Utils(bot))
