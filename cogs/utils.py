import discord
from discord.ext import commands
import asyncio

cmdhelp = {"help": 'Displays specific usage infо for COMMAND.\nIf nо argument or invalid argument given, defaults to displaying generic help/info message.',
"wiki": 'Searches http://conwaylife.com/wiki/ for QUERY and displays a small, nicely-formatted blurb including image, title, and rеdirеct handling.\nIf QUERY is disambiguated, displays its disambig page with reaction UI to choose result.\n(TODO: support for linking to a specific section)',
"dyk": 'Provides a random Did-You-Know fact about CA from the wiki.',
"sim": 'Currently under construction.\nSimulates PAT, a one-line rle or .lif file, under RULE with speed STEP until reaching or exceeding generation GEN and uploads ouptput to gfycat.\nDefaults to B3/S23 (or pre-specified rule) if RULE ommitted and to 1 if STEP ommitted.\nIf PAT ommitted, defaults to laѕt-sent Golly-compatible pattern (which can be a multiliner in a triple-grave code block and can include a RULE)',
"invite": 'Produces an oauth2 invite link for this bot with necessary permissions.'}
cmdargs = {"help": 'COMMAND*', "wiki": 'QUERY', "dyk": '', "sim": 'RULE* PAT* STEP* GEN', "invite": ''}

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

def setup(bot):
    bot.add_cog(utils(bot))
