import discord
from discord.ext import commands
import asyncio

# to expose to the eval command
import datetime
from collections import Counter

cmdhelp = {"help": 'Displays specific usage infо for COMMAND.\nIf nо argument or invalid argument given, defaults to displaying generic help/info message.',
"wiki": 'Searches http://conwaylife.com/wiki/ for QUERY and displays a small, nicely-formatted blurb including image, title, and rеdirеct handling.\nIf QUERY is disambiguated, displays its disambig page with reaction UI to choose result.\n(TODO: support for linking to a specific section)',
"dyk": 'Provides a random Did-You-Know fact about CA from the wiki.',
"sim": 'Currently under construction.\nSimulates PAT, a one-line rle or .lif file, under RULE with speed STEP until reaching or exceeding generation GEN and uploads ouptput to gfycat.\nDefaults to B3/S23 (or pre-specified rule) if RULE ommitted and to 1 if STEP ommitted.\nIf PAT ommitted, defaults to laѕt-sent Golly-compatible pattern (which can be a multiliner in a triple-grave code block and can include a RULE)',
"invite": 'Produces an oauth2 invite link for this bot with necessary permissions.'}
cmdargs = {"help": 'COMMAND*', "wiki": 'QUERY', "dyk": '', "sim": 'RULE* PAT* STEP* GEN', "invite": ''}

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None    # for !repl
        self.sessions = set()       # for !repl
        global oauth
        oauth = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
#       https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
    
    @commands.command(name='invite')
    async def invite(self, ctx):
        em = discord.Embed(description=f'Use [this link]({oauth}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @commands.command(name='help', aliases=['info'])
    async def help(self, ctx, *command: str):
        ctx.channel.trigger_typing()
        try:
            command = command[0]
            await ctx.send(f'```nginx\n{self.bot.command_prefix(self.bot, ctx.message)}{command} {cmdargs[command]}\n——————\n{cmdhelp[command]}```')
        except (KeyError, IndexError) as e:
            desc = '''**```ini
       [A cellular automata bot for Conwaylife.​com]```**```makefile
Commands:
{0}help   | Display this message
{0}wiki   | Look for a page on http://conwaylife.com/wiki/
{0}dyk    | Provide a random Did-You-Know from wiki
{0}sim    | Simulate a given CA pattern with output to gfycat
{0}invite | Post an invite link for this bot``````FORTRAN
        '{0}help COMMAND' for command-specific info```'''.format(self.bot.command_prefix(self.bot, ctx.message))
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)
            
    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'
    
    @commands.command(hidden=True, name='eval') # from Rapptz
    @commands.is_owner()
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(hidden=True) # from Rapptz
    @commands.is_owner()
    async def repl(self, ctx):
        """Launches an interactive REPL session."""
        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author,
            '_': None,
        }

        if ctx.channel.id in self.sessions:
            await ctx.send('Already running a REPL session in this channel. Exit it with `quit`.')
            return

        self.sessions.add(ctx.channel.id)
        await ctx.send('Enter code to execute or evaluate. `exit()` or `quit` to exit.')

        def check(m):
            return m.author.id == ctx.author.id and \
                   m.channel.id == ctx.channel.id and \
                   m.content.startswith('`')

        while True:
            try:
                response = await self.bot.wait_for('message', check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await ctx.send('Exiting REPL session.')
                self.sessions.remove(ctx.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await ctx.send('Exiting.')
                self.sessions.remove(ctx.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await ctx.send(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = f'```py\n{value}{traceback.format_exc()}\n```'
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = f'```py\n{value}{result}\n```'
                    variables['_'] = result
                elif value:
                    fmt = f'```py\n{value}\n```'

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await ctx.send('Content too big to be printed.')
                    else:
                        await ctx.send(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send(f'Unexpected error: `{e}`')

def setup(bot):
    bot.add_cog(Utils(bot))
