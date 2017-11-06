import discord
from discord.ext import commands
import os

def get_prefix(bot, message):
    try:
        in_lounge = message.guild.id == 357922255553953794
        return '!' if in_lounge else 'ca.'
    except AttributeError as e: # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!'

bot = commands.Bot(command_prefix=get_prefix, description="A 'caterer' bot for the cellular automata community's Discord server")
bot.remove_command('help') # lul

cogs = ['cogs.utils', 'cogs.wiki', 'cogs.ca', 'cogs.admin']

@bot.event
async def on_ready():
    if __name__ == '__main__':
        for cog in cogs:
            try:
                bot.load_extension(cog)
            except Exception as e:
                print(f'Error loading extension {cog}: {e}')
    print(f'Discord: {discord.__version__}')
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(os.getenv('DISCORD_TOKEN'))
