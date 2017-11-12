import discord
import asyncio
from discord.ext import commands
from cogs.resources import cmd
from platform import python_version

class Utils:
    def __init__(self, bot):
        self.bot = bot
        self._invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
      # https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
    
    @commands.command(name='link', aliases=cmd.aliases['link'])
    async def link(self, ctx):
        em = discord.Embed(description=f'Use [this link]({self._invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
             
            
    
    @commands.command(name='help', aliases=cmd.aliases['help'])
    async def help(self, ctx, command=None):
        ctx.channel.trigger_typing()
        prefix = self.bot.command_prefix(self.bot, ctx.message)
        if command not in cmd.aliases:
            command = [v for v in cmd.aliases if command in cmd.aliases[v]]
            command = command[0] if command else None
        if command:
            msg = f'```nginx\n{prefix}{command} {cmd.args[command]}``````apache\n{cmd.desc[command]}```'
            if cmd.aliases[command]:
                msg += '```apache\nAliases: {}```'.format(', '.join(prefix+i for i in cmd.aliases[command]))
            await ctx.send(msg)
        else:
            desc = '''**```ini
    [A cellular automata bot for Conwaylife.com]```**```makefile
Commands:
{0}help | Display this message
{0}wiki | Look for a page on http://conwaylife.com/wiki/
{0}dyk  | Provide a random Did-You-Know fact from wiki
{0}sim  | Simulate a given CA pattern with GIF output
{0}link | Post an invite link for this bot``````FORTRAN
   {1}'{0}help COMMAND' for command-specific docs
   {1}'{0}info' for credits & general information```'''.format(prefix, '  ' if prefix == '!' else ' ')
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)
    
    @commands.command(name='info', aliases=cmd.aliases['info'])
    async def info(self, ctx):
        await ctx.send(embed=discord.Embed(description=f'''**```ini
 [A cellular automata bot for Conwaylife.com] ```**
 **Version numbers:**
   python {python_version()}
   discord.py {discord.__version__} (rewrite)

 **Thanks to:**
   + Scorbie (GitHub contributor)
   + Conwaylife Lounge members (ideas & encouragement and stuff)
   + d-api (noob question support)
   + Hosted on Heroku

 **Links:**
   [GitHub repo](https://github.com/eltrhn/conwaylife-butler)
   [Conwaylife.com forums](http://conwaylife.com/forums)
   [Support server/testnet](https://discord.gg/6A6hM72)

 **By Wright**
```FORTRAN
          '{self.bot.command_prefix(self.bot, ctx.message)}help' for command info```'''))
        
    
    async def try_delete(self, sent, caller): # no fun allowed
        try:
            await self.bot.wait_for('message_delete', timeout=30.0, check=lambda m: m.id == caller.id)
        except asyncio.TimeoutError:
            pass
        else:
            await sent.delete()
    
    @commands.command(name='no', aliases=cmd.aliases['no']) # extremely useful
    async def no(self, ctx):
        await self.try_delete(await ctx.send('no'), ctx.message)

    
    @commands.command(name='yes', aliases=cmd.aliases['yes']) # slightly less useful
    async def yes(self, ctx):
        await self.try_delete(await ctx.send('yes'), ctx.message)

def setup(bot):
    bot.add_cog(Utils(bot))
