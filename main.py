import discord
from discord.ext import commands
import os, traceback, re
rNUM = re.compile(r'line (\d+),')

def get_prefix(bot, message):
    in_lounge = message.guild.id == 357922255553953794
    is_tester = bot.user.id == 376485072561504257
    try:
        return ('!', '?')[is_tester] if in_lounge else 'ca.'
    except AttributeError as e: # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!' #TODO: subclass bot or something to make this able to be ''

bot = commands.Bot(command_prefix=get_prefix, description="A 'caterer' bot for the cellular automata community's Discord server")
bot.remove_command('help') # lul

extensions = ['cogs.utils', 'cogs.wiki', 'cogs.ca', 'cogs.admin', 'cogs.role_stuffs']

@bot.event
async def on_ready():
    if __name__ == '__main__':
        for cog in extensions:
            try:
                bot.load_extension(cog)
            except Exception as e:
                exc = traceback.format_exception(type(e), e, e.__traceback__)
                line = rNUM.search(exc[-2]).group(1)
                print(f'{e.__class__.__name__} in {cog}, line {line}: {e}')
    print(f'Discord: {discord.__version__}')
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('Guilds:', ', '.join(f'{i.id} "{i.name}"' for i in bot.guilds) if len(bot.guilds) < 10 else len(bot.guilds))
    print('------')

bot.run(os.getenv('DISCORD_TOKEN'))
