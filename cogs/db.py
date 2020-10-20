import os
import subprocess

import discord
from discord.ext import commands

from cogs.resources import mutils


class DB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))

    @mutils.command('Query the 5S database')
    async def sssss(self, ctx, velocity):
        """
        # Queries the Smallest Spaceship Supporting Specific Speeds (5S) database #
        <[ARGS]>
        VELOCITY: The velocity of the spaceship
        """

        preface = f'{self.dir}/resources/bin/CAViewer'
        if velocity[-1] == "o": database = f'{self.dir}/resources/db/orthogonal.sss.txt'
        elif velocity[-1] == "d": database = f'{self.dir}/resources/db/diagonal.sss.txt'
        else: database = f'{self.dir}/resources/db/oblique.sss.txt'

        p = subprocess.Popen(
            f"{preface} 5s -v {velocity} -db {database}".split(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()

        err = out[1].decode("utf-8")
        if err: return await ctx.send(f"```{err}```")
        else: return await ctx.send(f"```{out[0].decode('utf-8')}```")

    @mutils.command('Query the SOSSP database')
    async def sossp(self, ctx, period):
        """
        # Queries the Smallest Oscillators Supporting Specific Periods (SOSSP) database #
        <[ARGS]>
        PERIOD: The period of the oscillator
        """

        preface = f'{self.dir}/resources/bin/CAViewer'
        database = f'{self.dir}/resources/db/sossp.sss.txt'

        period = period.replace("P", "")
        p = subprocess.Popen(
            f"{preface} 5s -p {int(period)} -db {database}".split(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()

        err = out[1].decode("utf-8")
        if err: return await ctx.send(f"```{err}```")
        else: return await ctx.send(f"```{out[0].decode('utf-8')}```")


def setup(bot):
    bot.add_cog(DB(bot))
