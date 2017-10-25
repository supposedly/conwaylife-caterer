import discord
from discord.ext import commands
import asyncio

cmdhelp = {"help": '[CMD]: Command to display usage info for. If ommitted, defaults to displaying generic help/info message.',

"wiki": '''[QUERY]: Page title to search http://conwaylife.com/wiki/ for. If disambiguated, displays its disambig page with reaction UI allowing user to choose desired page.
Displays a small, nicely-formatted blurb from QUERY's page including image, title, and rеdirеct handling.

(TODO: no arguments displays PoTW, subsection links)''',

"dyk": '''Provides a random Did-You-Know fact from wiki.''',

"sim": '''[PAT]: One-line rle or .lif file to simulate. If ommitted, uses last-sent Golly-compatible pattern (which can be a multiliner in a triple-grave code block).
[RULE]: Rulestring to simulate PAT under. If ommitted, defaults to B3/S23 or rule specified in PAT.
[GEN]: Generation to simulate up to. Mandatory.
[STEP]: Step size. Affects simulation speed. If ommitted, defaults to 1.
[g]: If present, uploads GIF output to gfycat. Otherwise sends directly through Discord.

Currently under construction.''',

"invite": '''Produces an oauth2 invite link for this bot with necessary permissions.'''}

cmdargs = {"help": 'CMD*', "wiki": 'QUERY', "dyk": '', "sim": 'RULE* PAT* GEN STEP* g*', "invite": ''}

class utils:
    def __init__(self, bot):
        self.bot = bot
        self.invite = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=388160))
#       https://discordapp.com/oauth2/authorize?client_id=359067638216785920&scope=bot&permissions=388160
    
    @commands.command(name='invite')
    async def invite(self, ctx):
        em = discord.Embed(description=f'Use [this link]({self.invite}) to add me to your server!', color=0x000000)
        em.set_author(name='Add me!', icon_url=self.bot.user.avatar_url)
        await ctx.send(embed=em)
    
    @commands.command(name='help', aliases=['info'])
    async def help(self, ctx, *command: str):
        ctx.channel.trigger_typing()
        try:
            command = command[0]
            await ctx.send(f'```nginx\n{self.bot.command_prefix(self.bot, ctx.message)}{command} {cmdargs[command]}``````ini{cmdhelp[command]}```')
        except (KeyError, IndexError) as e:
            desc = '''**```ini
       [A cellular automata bot for Conwaylife.​com]```**```makefile
Commands:
{0}help   | Display this message
{0}wiki   | Look for a page on http://conwaylife.com/wiki/
{0}dyk    | Provide a random Did-You-Know fact from wiki
{0}sim    | Simulate a given CA pattern with GIF output
{0}invite | Post an invite link for this bot``````FORTRAN
        '{0}help COMMAND' for command-specific info```'''.format(self.bot.command_prefix(self.bot, ctx.message))
            em = discord.Embed(description=desc)
            await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(utils(bot))
