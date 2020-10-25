import os
import re
import subprocess

from discord.ext import commands

from cogs.resources import mutils

WRIGHT = 180809886374952960

rXRLE = re.compile(
    r'x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?\n([\d.A-Z]*[.A-Z$][\d.A-Z$\n]*!?|[\dob$]*[ob$][\dob$\n]*!?)',
    re.I)


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

        if re.match("^\\d*c/\\d+$", velocity):
            velocity += "o"
        elif re.match("^\\d*c$", velocity):
            velocity += "/1o"

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
        if err:
            return await ctx.send(f"```{err}```")
        else:
            return await ctx.send(f"```{out[0].decode('utf-8')}```")

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
        if err:
            return await ctx.send(f"```{err}```")
        else:
            return await ctx.send(f"```{out[0].decode('utf-8')}```")

    @mutils.command('Query the GliderDB database', args=True)
    async def gliderdb(self, ctx, *, flags):
        """
        # Queries the (Higher Range) Outer Totalistic (Generations) GliderDB database #
        <[FLAGS]>
        -p: The period of the spaceship
        -dx: The displacement in the x-direction
        -dy: The displacement in the y-direction
        -min: The minimum rule to look for
        -max: The maximum rule to look for
        -sort: Sorts the output. Choose from [period, slope, population]
        -r: Range of the rule to query (for HROT DB)
        -n: The neighbourhood of the database to query (for HROT DB)
        -gen: Query the generations GliderDB instead
        """

        try:
            period = int(flags.get('p', -1))
            dx = int(flags.get('dx', -1))
            dy = int(flags.get('dy', -1))
            min_rule = flags.get('min', 'non')
            max_rule = flags.get('max', 'non')
            sort = flags.get('sort', '')
            if not re.match("(period|slope|population|\\s*)", sort):
                return await ctx.send("Error: sort must be one of [period, slope, population]")
        except Exception as e:
            return await ctx.send(f"Error: `{str(e)}`")

        await ctx.send("Searching GliderDB... Do not invoke command again until output is received.")

        if flags.get('gen', ''):  # Check for generations query
            database = f'{self.dir}/resources/db/generations-gliders.db.txt'
        elif flags.get('r', 1) != 1:  # For HROT
            database = f'{self.dir}/resources/db/R{flags.get("r", 2)}-N{flags.get("n", "M")}-gliders.db.txt'
        else:
            database = f'{self.dir}/resources/db/new-gliders.db.txt'

        try:
            open(database, "r")
        except FileNotFoundError:
            return await ctx.send(f"Error: DB file could not be found!")

        try:
            resp = await mutils.await_event_or_coro(
                self.bot,
                event='reaction_add',
                coro=self.invoke_db(period, dx, dy, min_rule, max_rule, sort, database)
            )
        except MemoryError:
            return await ctx.send(f"Error: Ran out of memory :frowning:")
        except Exception as e:
            return await ctx.send(f"Error: `{str(e)}`")

        out = resp["event"]

        if out[1].decode("utf-8"):
            return await ctx.send(f"Error: ```{out[1].decode('utf-8')}```")

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

        await ctx.send(f"This query found {count - 1} ships in total.")

    @mutils.command('Generates an entry for the GliderDB database')
    async def entry(self, ctx):
        """
        # Generates an entry for the GliderDB database #
        """

        pat = ""
        async for msg in ctx.channel.history(limit=50):
            rmatch = rXRLE.search(msg.content)
            if rmatch:
                pat = rmatch.group()
                break
        if not pat:
            return await ctx.send(f"`Error: No PAT found in last 50 messages.`")

        current = f'{self.dir}/{ctx.message.id}'
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat)

        try:
            resp = await mutils.await_event_or_coro(
                self.bot,
                event='reaction_add',
                coro=self.gen_entry(f'{current}_in.rle')
            )
        except MemoryError:
            return await ctx.send(f"Error: Ran out of memory :frowning:")
        except Exception as e:
            return await ctx.send(f"Error: `{str(e)}`")

        out = resp["event"]
        if out[1].decode("utf-8"):
            return await ctx.send(f"Error: ```{out[1].decode('utf-8')}```")

        return await ctx.send("```" + out[0].decode("utf-8") + "```")

    async def gen_entry(self, file):
        preface = f'{self.dir}/resources/bin/CAViewer'
        p = subprocess.Popen(
            f"{preface} entry -i {file}".split(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = await self.bot.loop.run_in_executor(None, p.communicate)

        return out

    async def invoke_db(self, period, dx, dy, min_rule, max_rule, sort, database):
        preface = f'{self.dir}/resources/bin/CAViewer'

        max_mem = int(os.popen('free --kilo').read().split()[7]) - 1000  # Leave 1 MB just in case

        if sort != "":
            p = subprocess.Popen(
                f"ulimit -m {max_mem} -v {max_mem}\n{preface} db -db {database} -p {period} -dx {dx} -dy {dy} "
                f"--max_rule {max_rule} --min_rule {min_rule} --sort {sort}",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        else:
            p = subprocess.Popen(
                f"ulimit -m {max_mem} -v {max_mem}\n{preface} db -db {database} -p {period} -dx {dx} -dy {dy} "
                f"--max_rule {max_rule} --min_rule {min_rule}",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out = await self.bot.loop.run_in_executor(None, p.communicate)

        return out


def setup(bot):
    bot.add_cog(DB(bot))
