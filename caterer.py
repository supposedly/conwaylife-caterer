import asyncio
import collections
import copy
import os
import select
import subprocess

import aiofiles
import asyncpg
import discord
from discord.ext import commands

from cogs.resources import mutils


def get_prefix(bot, message):
    try:
        return ['ca.'] + ([('!', ';')[bot.user.id == 376485072561504257]] if message.guild.id == 357922255553953794 else [])
    except AttributeError:  # if in DMs, message.guild is None and therefore has no attribute 'id'
        return '!'  # TODO: override commands.Bot.get_prefix to allow this to be ''


class Context(commands.Context):
    async def update(self):
        self.message = await self.get_message(self.message.id)
    
    async def upd_rxns(self):
        await self.update()
        return self.message.reactions
    
    async def thumbsup(self, override=True):
        try:
            if not override and any(rxn.emoji in '👍👎' for rxn in await self.upd_rxns() if rxn.me):
                return
            await self.message.add_reaction('👍')
        except discord.NotFound:
            pass
    
    async def thumbsdown(self, override=True):
        try:
            if not override and any(rxn.emoji in '👍👎' for rxn in await self.upd_rxns() if rxn.me):
                return
            await self.message.add_reaction('👎')
        except discord.NotFound:
            pass
    
    async def invoke(self, *args, **kwargs):
        return await super().invoke(*args, **kwargs, __invoking=True)
    

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.first_time = True
        self.owner = None
        self.assets_chn = None
        super().__init__(*args, **kwargs)
    
    async def on_message(self, message):
        await self.invoke(await self.get_context(message, cls=Context))
    
    async def approve_asset(self, file, filename, blurb, kind, *, approval='✅', rejection='❌'):
        msg = await self.assets_chn.send(f'{kind.upper()}: {blurb}', file=discord.File(copy.copy(file), filename))
        await msg.add_reaction(approval)
        await msg.add_reaction(rejection)
        file.seek(0)
        def check(rxn, usr):
            # ...not going to check role IDs anymore, because if someone has access to
            # the caterer-assets channel it's likely a given that they're trusted
            return usr.id != self.user.id and rxn.message.id == msg.id and rxn.emoji in (approval, rejection)
        rxn, _ = await self.wait_for('reaction_add', check=check)  # no timeout
        await msg.delete()
        if rxn.emoji == approval:
            return True
        return False


bot = Bot(
  command_prefix=get_prefix,
  description='A cellular automata bot for Conwaylife.com',
  help_command=None
)

@bot.check
def ignore_bots(ctx):
    return not ctx.author.bot

@bot.event
async def on_ready():
    if bot.first_time:
        bot.pool = await asyncpg.create_pool(
          dsn=os.getenv('DATABASE_URL'), max_size=15, loop=bot.loop
        )
        bot.assets_chn = bot.get_channel(424383992666783754)
        bot.owner = (await bot.application_info()).owner
        for cog in ('meta', 'wiki', 'ca', 'admin'):
            try:
                bot.load_extension(f'cogs.{cog}')
            except Exception:
                raise
        bot.help_padding = 1 + max(len(i.name) for i in bot.commands)
        bot.sorted_commands = sorted(bot.commands, key=lambda x: x.name)
        print(f'Logged in as\n{bot.user.name}\n{bot.user.id}')
        print('Guilds:', len(bot.guilds))
        print('------')
        bot.first_time = False

bot.run(os.getenv('DISCORD_TOKEN'))
