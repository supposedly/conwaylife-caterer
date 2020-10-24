import os
import re
import urllib.request
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

        if "c/3.14" in velocity:
            return await ctx.send("```#C (1,0)c/137\n#C Population: 22/7\nx = 3, y = 14, rule = "
                                  "B3/S23\n3o$ob4obob5ob9o!```")

        if re.match("^\\d*c/\\d+$", velocity): velocity += "o"
        elif re.match("^\\d*c$", velocity): velocity += "/1o"

        preface = f'{self.dir}/resources/bin/CAViewer'
        if velocity[-1] == "o":
            database = f'{self.dir}/resources/db/orthogonal.sss.txt'
        elif velocity[-1] == "d":
            database = f'{self.dir}/resources/db/diagonal.sss.txt'
        else:
            database = f'{self.dir}/resources/db/oblique.sss.txt'

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

    @mutils.command('Query the GliderDB database')
    async def gliderdb(self, ctx):
        """
        # Queries the Outer Totalistic GliderDB database #
        <[FLAGS]>
        -p: The period of the spaceship
        -dx: The displacement in the x-direction
        -dy: The displacement in the y-direction
        -min: The minimum rule to look for
        -max: The maximum rule to look for
        -sort: Sorts the output. Choose from [period, slope, population]
        """

        flags = ctx.message.content.split(" ")

        period = -1
        if "-p" in flags: period = int(flags[flags.index("-p") + 1])

        dx = -1
        if "-dx" in flags: dx = int(flags[flags.index("-dx") + 1])

        dy = -1
        if "-dy" in flags: dy = int(flags[flags.index("-dy") + 1])

        min_rule = "non"
        if "-min" in flags: min_rule = flags[flags.index("-min") + 1]

        max_rule = "non"
        if "-max" in flags: max_rule = flags[flags.index("-max") + 1]

        sort = ""
        if "-sort" in flags: max_rule = flags[flags.index("-sort") + 1]
        if not re.match("(period|slope|population|\\s*)", sort):
            return await ctx.send("Error: -sort must be one of [period, slope, population]")

        preface = f'{self.dir}/resources/bin/CAViewer'
        database = f'{self.dir}/resources/db/new-gliders.db.txt'
        if sort != "":
            p = subprocess.Popen(
                f"{preface} db -db {database} -p {period} -dx {dx} -dy {dy} --max_rule {max_rule} "
                f"--min_rule {min_rule} --sort {sort}".split(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            p = subprocess.Popen(
                f"{preface} db -db {database} -p {period} -dx {dx} -dy {dy} --max_rule {max_rule} "
                f"--min_rule {min_rule}".split(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()

        err = out[1].decode("utf-8")
        if err: return await ctx.send(f"```{err}```")

        rle = ""
        output = out[0].decode("utf-8")

        count = 0
        for line in output.split("\n"):
            if re.match("^\\s*$", line):
                count += 1
                if count < 21 and rle != "": await ctx.send(f"```{rle}```")
                if count == 21: await ctx.send("20 ships have been outputted. "
                                               "No more ships will be outputted to avoid cluttering the channel.")
                rle = ""
            else:
                rle += line + "\n"

        await ctx.send(f"This query found {count} ships in total.")


def setup(bot):
    bot.add_cog(DB(bot))
