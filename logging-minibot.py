import asyncio
import collections
import os
import select
import subprocess
from itertools import islice

import discord
from discord.ext import commands


def get_prefix(bot, message):
    try:
        return ['ca.'] + ([('!', ';')[bot.user.id == 376485072561504257]] if message.guild.id == 357922255553953794 else [])
    except AttributeError as e: # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!' #TODO: override commands.Bot.get_prefix to allow this to be ''

bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')

@bot.event
async def on_ready():
    bot.logs = collections.deque(maxlen=100)
    bot.logtask = bot.loop.create_task(get_heroku_logs())
    print('Logbot ready!')

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

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return
    raise error

@bot.command()
async def logs(ctx, start: int = 0):
    start = max(0, min(len(bot.logs)-20, start))
    log = await ctx.send(
      f'**{len(bot.logs)-start-20}..{len(bot.logs)-start} of {len(bot.logs)} log entries**\n'
      '```css\n'
      + ''.join(reversed(list(islice(bot.logs, start, 20+start))))
      + '```'
    )
    while True:
        available = '⬆⬇'[start>=len(bot.logs)-20 : 1+bool(start)]
        [await log.add_reaction(i) for i in available]
        try:
            rxn, usr = await bot.wait_for(
              'reaction_add',
              timeout = 30.0,
              check = lambda rxn, usr: all((rxn.emoji in available, usr is ctx.message.author, rxn.message.id == log.id))
              )
        except asyncio.TimeoutError:
            return await log.clear_reactions()
        await log.clear_reactions()
        start = max(0, min(len(bot.logs)-20, start+10*((rxn.emoji=='⬆')-(rxn.emoji=='⬇'))))
        await log.edit(content =
          f'**{len(bot.logs)-start-20}..{len(bot.logs)-start} of {len(bot.logs)} log entries**\n'
          '```css\n'
          + ''.join(reversed(list(islice(bot.logs, start, 20+start))))
          + '```'
        )
        
bot.run(os.getenv('DISCORD_TOKEN'))
