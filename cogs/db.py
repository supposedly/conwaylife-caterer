import os
import re
import subprocess
import urllib.request
import urllib.error

from discord.ext import commands

from cogs.resources import mutils

WRIGHT = 180809886374952960

rXRLE = re.compile(
    r'x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?\n([\d.A-Z]*[.A-Z$][\d.A-Z$\n]*!?|[\dob$]*[ob$][\dob$\n]*!?)',
    re.I)


def get_birth_survival(rule):
    if re.fullmatch("[Bb][0-9]*/?[Ss][0-9]*[VH]?", rule):  # Outer Totalistic
        birth, survival = rule.split("/")
        birth = birth[1:]
        survival = survival[1:].replace("V", "").replace("H", "")

        return set([int(i) for i in birth]), set([int(i) for i in survival])
    elif re.fullmatch("[0-9]*/[0-9]*/[0-9]+[VH]?", rule):  # Generations
        survival, birth, num_states = rule.split("/")
        birth = birth[1:]
        survival = survival[1:]

        return set([int(i) for i in birth]), set([int(i) for i in survival])
    else:  # Higher-range outer totalistic
        birth = re.findall("B(((\\d,(?=\\d))|(\\d-(?=\\d))|\\d)+)?", rule)[0][0].split(",")
        survival = re.findall("S(((\\d,(?=\\d))|(\\d-(?=\\d))|\\d)+)?", rule)[0][0].split(",")

        birth_lst = set()
        survival_lst = set()
        for i in birth:
            if "-" in i:
                for j in range(int(i.split("-")[0]), int(i.split("-")[1])):
                    birth_lst.add(j)
            else:
                birth_lst.add(int(i))

        for i in survival:
            if "-" in i:
                for j in range(int(i.split("-")[0]), int(i.split("-")[1])):
                    survival_lst.add(j)
            else:
                survival_lst.add(int(i))

        return birth_lst, survival_lst


def between_min_max(minimum, maximum, transition):
    return transition.issubset(maximum) and minimum.issubset(transition)


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
        -desc: Sorts the output in descending order

        -r: Range of the database to query
        -n: The neighbourhood of the database to query
        -c: Number of states of the database to query
        -osc: Query the oscillator database instead
        """

        try:
            period = int(flags.get('p', -1))
            dx = int(flags.get('dx', -1))
            dy = int(flags.get('dy', -1))
            min_rule = flags.get('min', '')
            max_rule = flags.get('max', '')
            sort = flags.get('sort', '')
            desc = flags.get('desc', False)
            if not re.match("(period|slope|population|\\s*)", sort):
                return await ctx.send("Error: sort must be one of [period, slope, population]")

            states = int(flags.get("c", 2) if flags.get("c", 2) != 0 else 2)
            rule_range = int(flags.get("r", 1))
            neighbourhood = flags.get("n", "M").upper()
        except Exception as e:
            return await ctx.send(f"Error: `{str(e)}`")

        if 'osc' in flags:
            database = f'https://raw.githubusercontent.com/jedlimlx/HROT-Glider-DB/master/R{rule_range}-' \
                       f'C{states}-' \
                       f'N{neighbourhood}-oscillators.db.txt'
        else:
            database = f'https://raw.githubusercontent.com/jedlimlx/HROT-Glider-DB/master/R{rule_range}-' \
                       f'C{states}-' \
                       f'N{neighbourhood}-gliders.db.txt'

        try:
            with open(f"{self.dir}/resources/db/database.txt", "w") as f:
                fp = urllib.request.urlopen(database)
                mybytes = fp.read()
                fp.close()

                f.write(mybytes.decode("utf-8"))
        except urllib.error.HTTPError:
            return await ctx.send(f"Error: DB file could not be found!")

        await ctx.send("Searching GliderDB... Do not invoke command again until output is received.")

        results = []
        if dx != -1 and dy == -1: dy = 0
        if dy != -1 and dx == -1: dx = 0
        if min_rule != "": min_birth, min_survival = get_birth_survival(min_rule)
        if max_rule != "": max_birth, max_survival = get_birth_survival(max_rule)
        with open(f"{self.dir}/resources/db/database.txt", "r") as f:
            count = 0
            lines = f.readlines()
            message = None
            for line in lines:
                tokens = line.split(":")
                if (period == -1 or int(tokens[4].replace("/2", "")) == period) and (
                        dx == -1 or dy == -1 or (abs(int(tokens[5])) == abs(dx) and abs(int(tokens[6])) == abs(dy)) or
                        (abs(int(tokens[5])) == abs(dy) and abs(int(tokens[6])) == abs(dx))):
                    if min_rule == "" or max_rule == "":
                        tokens[-1] = tokens[-1].replace("o", "A").replace("b", ".").replace("\n", "")
                        results.append(tokens)
                        continue

                    min_birth_2, min_survival_2 = get_birth_survival(tokens[2])
                    max_birth_2, max_survival_2 = get_birth_survival(tokens[3])
                    if (between_min_max(min_birth, max_birth, min_birth_2) and
                            between_min_max(min_survival, max_survival, min_survival_2)) or (
                            between_min_max(min_birth, max_birth, max_birth_2) and
                            between_min_max(min_survival, max_survival, max_survival_2)):
                        tokens[-1] = tokens[-1].replace("o", "A").replace("b", ".").replace("\n", "")
                        results.append(tokens)

                count += 1
                if count % 1000 == 0:
                    if message is not None: await message.delete()
                    message = await ctx.send(f"Read {count} entries")

        if sort == "period":
            results = sorted(results, key=lambda k: k[4], reverse=desc)
        elif sort == "slope":
            results = sorted(results, key=lambda k: (abs(int(k[5])), abs(int(k[6]))), reverse=desc)
        elif sort == "population":
            results = sorted(results, key=lambda k: sum(map(lambda s: s and int(s) or 1, re.sub(r"\d*[.B-Z$]|!", "", k[-1]).split("A"))) - 1, reverse=desc)  # Code-golf by AForAwesome

        for tokens in results:
            if tokens[5] == "0" and tokens[6] == "0": pattern = f"P{tokens[4].replace('/2', '')}"
            else: pattern = f"({tokens[5]}, {tokens[6]})c/{tokens[4].replace('/2', '')}"

            pop = sum(map(lambda s: s and int(s) or 1, re.sub(r'\d*[.B-Z$]|!', '', tokens[-1]).split('A'))) - 1
            await ctx.send(f"```#C {pattern} {tokens[0]}\n"
                           f"#C Discovered by: {tokens[1]}\n"
                           f"#C Min Rule: {tokens[2]}\n"
                           f"#C Max Rule: {tokens[3]}\n"
                           f"#C Population: {pop}\n"
                           f"x = {tokens[-3]}, y = {tokens[-2]}, rule = {tokens[2]}\n"
                           f"{tokens[-1]}```")
        await ctx.send(f"This query found {len(results)} ships.")

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


def setup(bot):
    bot.add_cog(DB(bot))
