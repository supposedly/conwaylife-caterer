import asyncio
import collections
import os
import re
import select
import subprocess
import traceback

import asyncpg
import discord
from discord.ext import commands

rNUM = re.compile(r'line (\d+),')


class Context(commands.Context):
    async def thumbsup(self):
        return await self.message.add_reaction('👍')
    async def thumbsdown(self):
        return await self.message.add_reaction('👎')


class Bot(commands.Bot):
    async def on_message(self, message):
        await self.invoke(await self.get_context(message, cls=Context))


def get_prefix(bot, message):
    try:
        return ['ca.'] + ([('!', ';')[bot.user.id == 376485072561504257]] if message.guild.id == 357922255553953794 else [])
    except AttributeError as e: # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!' #TODO: override commands.Bot.get_prefix to allow this to be ''


bot = Bot(command_prefix=get_prefix, description="A 'caterer' bot for the cellular automata community's Discord server")
bot.remove_command('help')

extensions = ['cogs.botutils', 'cogs.wiki', 'cogs.ca', 'cogs.admin']

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
    
    bot.help_padding = 1 + max(len(i.name) for i in bot.commands)
    bot.sorted_commands = sorted(bot.commands, key=lambda x: x.name)
    
    bot.logs = collections.deque(maxlen=100)
    bot.logtask = bot.loop.create_task(get_heroku_logs())
    
    print(f'Logged in as\n{bot.user.name}\n{bot.user.id}')
    print('Guilds:', len(bot.guilds))
    print('------')

async def get_heroku_logs():
    with subprocess.Popen('./open-logs.sh', stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) as proc:
        print('Received logs!')
        while not bot.is_closed():
            readables, _, _ = select.select([proc.stdout], [], [], 2.0)
            if not readables: # []
                await asyncio.sleep(2)
                continue
            line = proc.stdout.readline()
            if 'app[api]' not in line.split(': ')[0]:
                bot.logs.appendleft(f':{line.split(" ")[1].split("[")[0]} {line.split(": ", 1)[1]}')

bot.run(os.getenv('DISCORD_TOKEN'))
