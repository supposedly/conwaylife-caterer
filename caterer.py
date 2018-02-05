import os
import re
import traceback

import asyncpg
import discord
from discord.ext import commands

rNUM = re.compile(r'line (\d+),')

def get_prefix(bot, message):
    try:
        return ['ca.'] + ([('!', ';')[bot.user.id == 376485072561504257]] if message.guild.id == 357922255553953794 else [])
    except AttributeError as e: # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!' #TODO: subclass bot to make this able to be ''

bot = commands.Bot(command_prefix=get_prefix, description="A 'caterer' bot for the cellular automata community's Discord server")
bot.remove_command('help')

extensions = ['cogs.botutils', 'cogs.wiki', 'cogs.ca', 'cogs.admin', 'cogs.role_stuffs']

@bot.event
async def on_ready():
    bot.pool = await asyncpg.create_pool(dsn=os.getenv('DATABASE_URL'), max_size=15, loop=bot.loop)
    for cog in extensions:
        try:
            bot.load_extension(cog)
        except Exception as e:
            exc = traceback.format_exception(type(e), e, e.__traceback__)
            line = rNUM.search(exc[-2]).group(1)
            print(f'{e.__class__.__name__} in {cog}, line {line}: {e}')
    print(f'Logged in as\n{bot.user.name}\n{bot.user.id}')
    print('Guilds:', ', '.join(f'{i.id} "{i.name}"' for i in bot.guilds) if len(bot.guilds) < 10 else len(bot.guilds))
    print('------')

bot.run(os.getenv('DISCORD_TOKEN'))
