import asyncio
import concurrent
import copy
import io
import itertools
import json
import math
import os
import random
import re
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import aiofiles
import discord
import imageio
import png
from discord.ext import commands
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

from cogs.resources import mutils


# matches LtL rulestring
rLtL = re.compile(r'R\d{1,3},C\d{1,3},M[01],S\d+\.\.\d+,B\d+\.\.\d+,N[NM]', re.I)

# matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring
rRULESTRING = re.compile(r'(B)?(?:[0-8]-?[cekainyqjrtwz]*)+(?(1)/?(S)?(?:[0-8]-?[cekainyqjrtwz]*)*|/(S)?(?:[0-8]-?[cekainyqjrtwz]*)*(?(2)|(?(3)|/[\d]{1,3})?))', re.I)

# matches multiline XRLE; currently cannot, however, match headerless patterns (my attempts thus far have forced re to take much too many steps)
# does not match rules with >24 states
rXRLE = re.compile(r'x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?\n([\dob$]*[ob$][\dob$\n]*!?|[\d.A-Z]*[.A-Z$][\d.A-Z$\n]*!?)')

# splits RLE into its runs
rRUNS = re.compile(r'([0-9]*)([a-z][A-Z]|[ob.A-Z])')
# [rRUNS.sub(lambda m:''.join(['0' if m.group(2) == 'b' else '1' for x in range(int(m.group(1)) if m.group(1) else 1)]), pattern) for pattern in patlist[i]]

# unrolls $ signs
rDOLLARS = re.compile(r'(\d+)\$')

# determines 80% of available RAM to allow bgolly to use
MAX_MEM = int(os.popen('free -m').read().split()[7]) // 1.25

# ---- #

def parse(current):
    with open(f'{current}_out.rle', 'r') as pat:
        patlist = [line.rstrip('\n') for line in pat]

    os.remove(f'{current}_out.rle')
    # `positions` needs to be a list, not a generator
    # because it's returned from this function, so
    # it gets pickled by run_in_executor -- and
    # generators can't be pickled
    positions = [eval(i) for i in patlist[::3]]
    bboxes = [eval(i) for i in patlist[1::3]]
    
    # Determine the bounding box to make gifs from
    # The rectangle: xmin <= x <= xmax, ymin <= y <= ymax
    # where (x|y)(min|max) is the min/max coordinate across all gens.
    xmins, ymins = zip(*positions)
    (widths, heights), maxwidth, maxheight = zip(*bboxes), max(w for w, h in bboxes), max(h for w, h in bboxes)
    xmaxes = (xm+w for xm, w in zip(xmins, widths))
    ymaxes = (ym+h for ym, h in zip(ymins, heights))
    xmin, ymin, xmax, ymax = min(xmins), min(ymins), max(xmaxes), max(ymaxes)
    # Bounding box: top-left x and y, width and height
    bbox = xmin, ymin, xmax-xmin, ymax-ymin
    
    patlist = patlist[2::3] # just RLE
    # ['4b3$o', '3o2b'] -> ['4b$$$o', '3o2b']
    patlist = (rDOLLARS.sub(lambda m: ''.join(['$' for i in range(int(m.group(1)))]), j).replace('!', '') for j in patlist) # unroll newlines
    # ['4b$$$o', '3o2b'] -> [['4b', '', '', '', 'o'], ['3o', '2b']]
    patlist = [i.split('$') for i in patlist]
    return patlist, positions, bbox, (maxwidth, maxheight)

def makeframes(current, patlist, positions, bbox, pad, colors, bg, track, trackmaxes):
    xmin, ymin, width, height = bbox
    width, height = trackmaxes if track else (width, height)
    
    for index in range(len(patlist)):
        pat = patlist[index]
        xpos, ypos = positions[index]
        dx, dy = (1, 1) if track else (1+(xpos-xmin), 1+(ypos-ymin))
        frame = [bg * (2+width) for _ in range(2+height)]
        flat_pat = [
          [
            j for run, char in rRUNS.findall(row) for j in
            (bg if char in '.b' else colors[char]) * int(run or 1)
          ]
        for row in pat
        ]
        # Draw the pattern onto the frame by replacing segments of prerendered rows
        for i, flat_row in enumerate(flat_pat):
            frame[dy+i][3*dx:3*dx+len(flat_row)] = flat_row
        
        anchor = min(height, width)
        mul = -(-75 // anchor) if anchor <= 75 else 1
        frame = mutils.scale(tuple(mutils.scale(row, mul, 3) for row in frame), mul)
        
        with open(f'{current}_frames/{index:0{pad}}.png', 'wb') as out:
            w = png.Writer(len(frame[0])//3, len(frame))
            w.write(out, frame)

def savegif(current, gen, step):
    # finally, pass all created pics to imageio for conversion to gif
    # then either upload to gfycat or send directly to discord depending on presence of "g" flag
    png_dir = f'{current}_frames/'
    total = 0
    duration = min(1/6, max(1/60, 5/gen/step) if gen else 1)
    for subdir, dirs, files in os.walk(png_dir):
        files.sort()
        with imageio.get_writer(f'{current}.gif', mode='I', duration=str(duration)) as writer:
            for file in files:
                frame = imageio.imread(os.path.join(subdir, file))
                writer.append_data(frame)
                if os.stat(f'{current}.gif').st_size > 7600000:
                    return True
    return False

class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.ppe = ProcessPoolExecutor()
        self.tpe = ThreadPoolExecutor() # or just None
        self.loop = bot.loop
        self.defaults = *[[self.ppe, 'ProcessPoolExecutor']]*2, [self.tpe, 'ThreadPoolExecutor']
        self.opts = {'tpe': [self.tpe, 'ThreadPoolExecutor'], 'ppe': [self.ppe, 'ProcessPoolExecutor']}
    
    @staticmethod
    def genconvert(gen: int):
        if int(gen) > 0:
            return int(gen) - 1
        raise Exception # bad gen (less than or equal to zero)
    
    @staticmethod
    def makesoup(rulestring: str, x: int, y: int) -> str:
        """generates random soup as RLE with specified dimensions"""

        rle = f'x = {x}, y = {y}, rule = {rulestring}\n' # not really needed but it looks prettier :shrug:
                                                         # also prevents the length stuff below from erroring
        for row in range(y):
            pos = x
            while pos > 0:
                # below could also just be random.randint(1,x) but something likes this gives natural-ish-looking results
                runlength = math.ceil(-math.log(1-random.random()))
                if runlength > pos:
                    runlength = pos # or just `break`, no big difference qualitatively
                # switches o/b from last occurrence of the letter
                rle += (str(runlength) if runlength > 1 else '') + 'ob'['o' in rle[-3 if rle[-1] == '\n' else -1]]
                pos -= runlength
            rle += '$\n' if y > row + 1 else '!\n'
        return rle
    
    def cancellation_check(self, ctx, og_msg, rxn, usr):
        if rxn.message.id != og_msg.id:
            return False
        x_emoji = rxn.emoji == '❌'
        if usr != ctx.message.author:
            return x_emoji and rxn.count > 4
        return x_emoji

    async def do_gif(self, execs, current, gen, step, colors, track, bg):
        start = time.perf_counter()
        patlist, positions, bbox, trackmaxes = await self.loop.run_in_executor(execs[0][0], parse, current)
        end_parse = time.perf_counter()
        await self.loop.run_in_executor(execs[1][0], makeframes, current, patlist, positions, bbox, len(str(gen)), colors, bg, track, trackmaxes)
        end_makeframes = time.perf_counter()
        oversized = await self.loop.run_in_executor(execs[2][0], savegif, current, gen, step)
        end_savegif = time.perf_counter()
        return start, end_parse, end_makeframes, end_savegif, oversized
    
    async def run_bgolly(self, current, algo, gen, step, rule):
        # run bgolly with parameters
        preface = f'{self.dir}/resources/bgolly'
        ruleflag = f's {self.dir}/' if algo == 'RuleLoader' else f'r {rule}'
        return os.popen(f'{preface} -a "{algo}" -{ruleflag} -m {gen} -i {step} -o {current}_out.rle {current}_in.rle').read()
    
    def moreinfo(self, ctx):
        return f"'{ctx.prefix}help sim' for more info"
    
    @mutils.group('Simulate an RLE and output to GIF')
    async def sim(self, ctx, *args, **kwargs):
        """
        # Simulates PAT with output to animated gif. #
        <[FLAGS]>
        -h: Use HashLife instead of the default QuickLife.
        -time: Include time taken to create gif (in seconds w/hundredths) alongside GIF.
          all: Provide verbose output, showing time taken for each step alongside the type of executor used.
        -tag: When finished, tag requester. Useful for time-intensive simulations.
        -id: Has no function besides appearing above the final output, but can be used to tell apart simultaneously-created gifs.
        
        <[ARGS]>
        GEN: Generation to simulate up to.
        STEP: Step size. Affects simulation speed. If omitted, defaults to 1.
        RULE: Rulestring to simulate PAT under. If omitted, defaults to B3/S23 or rule specified in PAT.
        PAT: One-line rle or .lif file to simulate. If omitted, uses last-sent Golly-compatible pattern (which should be enclosed in a code block and therefore can be a multiliner).
        #TODO: streamline GIF generation process, implement proper LZW compression, implement flags & gfycat upload
        """
        _ = re.compile(r'^\d+$')
        rand = kwargs.pop('randpat', None)
        dims = kwargs.pop('soup_dims', None)
        (gen, step, rule, pat), flags = mutils.parse_args(
          args,
          [_, _, (rRULESTRING, rLtL), re.compile(r'[\dob$]*[ob$][\dob$\n]*!?')],
          ['', '1', '', '']
          )
        flags = mutils.parse_flags(flags)
        gen = self.genconvert(gen)
        bg = list(map(int, flags.get('bg', '255,255,255').split(',')))
        colors = {'o': (0,0,0), 'b': bg}
        if 'execs' in flags:
            flags['execs'] = flags['execs'].split(',')
            execs = [self.opts.get(v, self.defaults[i]) for i, v in enumerate(flags['execs'])]
        else:
            execs = self.defaults
        algo = 'HashLife' if 'h' in flags else 'QuickLife'
        track = 'track' in flags or 't' in flags
        try:
            step, gen = sorted([int(step), int(gen)]) if gen else [int(step), int(gen)]
        except ValueError:
            return await ctx.send(f"`Error: No GEN given. {self.moreinfo(ctx)}`")
        if gen / step > 2500:
            return await ctx.send(f"`Error: Cannot simulate more than 2500 frames. {self.moreinfo(ctx)}`")
        if rand:
            pat = rand
        if not pat:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rXRLE.search(msg.content)
                if rmatch:
                    pat = rmatch.group(2)
                    if rmatch.group(1):
                        rule = rmatch.group(1)
                    break
            if not pat:
                return await ctx.send(f"`Error: No PAT given and none found in last 50 messages. {self.moreinfo(ctx)}`")
        else:
            pat = pat.strip('`')
        
        if not rule:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rLtL.search(msg.content) or rRULESTRING.search(msg.content)
                if rmatch:
                    rule = rmatch.group()
                    break
            else:
                rule = ''
        
        current = f'{self.dir}/{ctx.message.id}'
        os.mkdir(f'{current}_frames')
        rule = ''.join(rule.split()) or 'B3/S23'
        algo = 'Larger than Life' if rLtL.match(rule) else algo if rRULESTRING.match(rule) else 'RuleLoader'
        if algo == 'RuleLoader':
            try:
                rulename, rulefile, n_states, colors = await self.bot.pool.fetchrow('''
                SELECT name, file, n_states, colors FROM rules WHERE name = $1::text
                ''', rule)
            except ValueError: # not enough values to unpack
                return await ctx.send('`Error: Rule not found`')
            
            colors = mutils.colorpatch(json.loads(colors), n_states, bg)
            with open(f'{self.dir}/{rulename}.rule', 'wb') as ruleout:
                ruleout.write(rulefile)
        details = (
          (f'Running `{dims}` soup' if rand else f'Running supplied pattern')
          + f' in rule `{rule}` with step `{step}` for `{1+gen}` generation(s)'
          + (f' using `{algo}`.' if algo != 'QuickLife' else '.')
          )
        announcement = await ctx.send(details)
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat if algo != 'RuleLoader' else f'x=0,y=0,rule={rule}\n{pat}')
        bg_err = await self.run_bgolly(current, algo, gen, step, rule)
        if bg_err:
            return await ctx.send(f'`{bg_err}`')
        await announcement.add_reaction('❌')
        resp = await mutils.await_event_or_coro(
                  self.bot,
                  event = 'reaction_add',
                  coro = self.do_gif(execs, current, gen, step, colors, track, bg),
                  ret_check = lambda obj: isinstance(obj, discord.Message),
                  event_check = lambda rxn, usr: self.cancellation_check(ctx, announcement, rxn, usr)
                  )
        try:
            start, end_parse, end_makeframes, end_savegif, oversized = resp['coro']
        except (KeyError, ValueError):
            return await resp['event'][0].message.delete()
        content = (
            (ctx.message.author.mention if 'tag' in flags else '')
          + (f' **{flags["id"]}** \n' if 'id' in flags else '')
          + '{time}'
          )
        try:
            gif = await ctx.send(
              content.format(
                time=str(
                  {
                    'Times': '',
                    '**Parsing frames**': f'{round(end_parse-start, 2)}s ({execs[0][1]})',
                    '**Saving frames**': f'{round(end_makeframes-end_parse, 2)}s ({execs[1][1]})',
                    '**Stitching frames to GIF**': f'{round(end_savegif-end_makeframes, 2)}s ({execs[2][1]})'
                  }
                ).replace("'", '').replace(',', '\n').replace('{', '\n').replace('}', '\n')
                if flags.get('time') == 'all'
                  else f'{round(end_savegif-start, 2)}s'
                  if 'time' in flags
                    else ''
                ) + ('\n(Truncated to fit under 8MB)' if oversized else ''),
              file=discord.File(f'{current}.gif')
              )
        except discord.errors.HTTPException as e:
            return await ctx.send(f'{ctx.message.author.mention}\n`HTTP 413: GIF too large. Try a higher STEP or lower GEN!`')
        try:
            while True:
                if gen < 2500 * step and not oversized:
                    await gif.add_reaction('➕')
                await gif.add_reaction('⏩')
                rxn, _ = await self.bot.wait_for('reaction_add', timeout=30.0, check=lambda rxn, usr: rxn.emoji in '➕⏩' and rxn.message.id == gif.id and usr is ctx.message.author)
                await gif.delete()
                os.system(f'rm -rf {current}_frames/'); os.mkdir(f'{current}_frames')
                if rxn.emoji == '➕':
                    gen += min(2500*step-gen, int(50*math.log1p(gen))) # gives a nice increasing-at-a-decreasing-rate curve
                else:
                    step *= 2
                    oversized = False
                details = (
                  (f'Running `{dims}` soup' if rand else f'Running supplied pattern')
                  + f' in rule `{rule}` with step `{step}` for `{gen+bool(rand)}` generation(s)'
                  + (f' using `{algo}`.' if algo != 'QuickLife' else '.')
                  )
                await announcement.edit(content=details)
                bg_err = await self.run_bgolly(current, algo, gen, step, rule)
                if bg_err:
                    return await ctx.send(f'`{bg_err}`')
                resp = await mutils.await_event_or_coro(
                  self.bot,
                  event = 'reaction_add',
                  coro = self.do_gif(execs, current, gen, step, colors, track, bg),
                  ret_check = lambda obj: isinstance(obj, discord.Message),
                  event_check = lambda rxn, usr: self.cancellation_check(ctx, announcement, rxn, usr)
                  )
                try:
                    start, end_parse, end_makeframes, end_savegif, oversized = resp['coro']
                except KeyError:
                    return await resp['event'].add_reaction('👍')
                try:
                    gif = await ctx.send(
                      content.format(
                        time = str(
                          {
                            'Times': '',
                            '**Parsing frames**': f'{round(end_parse-start, 2)}s ({execs[0][1]})',
                            '**Saving frames**': f'{round(end_makeframes-end_parse, 2)}s ({execs[1][1]})',
                            '**Stitching frames to GIF**': f'{round(end_savegif-end_makeframes, 2)}s ({execs[2][1]})'
                          }
                        ).replace("'", '').replace(',', '\n').replace('{', '\n').replace('}', '\n')
                        if flags.get('time') == 'all'
                          else f'{round(end_savegif-start, 2)}s'
                          if 'time' in flags
                            else ''
                        ) + ('\n`(truncated to fit under 8mb)`' if oversized else ''),
                      file=discord.File(f'{current}.gif')
                      )
                except discord.errors.HTTPException as e:
                    return await ctx.send(f'`HTTP 413: GIF too large. Try a higher STEP or lower GEN!`')
        except asyncio.TimeoutError:
            # will occur in the "forces-error" unpacking line above
            pass
        finally:
            await gif.clear_reactions()
            os.remove(f'{current}.gif')
            os.remove(f'{current}_in.rle')
            os.system(f'rm -rf {current}_frames/')
        
    @sim.command()
    async def rand(self, ctx, *args):
        """
        # Simulates a random soup in given rule with output to GIF. Dims default to 16x16. #
        <[FLAGS]>
        (None)
        {inherits}
        
        <[ARGS]>
        DIMS: "AxB" (sans quotes), where A and B are the desired soup's width and height separated by the literal character "x".
        {inherits}
        """
        # dims, rule, gen, step
        _ = re.compile(r'^\d+$')
        (dims, rule, *nums), flags = mutils.parse_args(
          args,
          [re.compile(r'^\d+x\d+$'), (rRULESTRING, rLtL), _, _],
          ['16x16', None, '300', None]
          )
        try:
            step, gen = sorted(int(i) for i in nums)
        except TypeError:
            try:
                step, gen = 1, list(filter(None, nums))[0]
            except IndexError:
                return await ctx.send(f'`Error: No GEN given. {self.moreinfo(ctx)}`')
        if not rule:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rLtL.search(msg.content) or rRULESTRING.search(msg.content)
                if rmatch:
                    rule = rmatch.group()
                    break
        x, y = dims.split('x')
        await ctx.invoke(
          self.sim,
          str(gen), # will this ever be int?
          str(step),
          rule or 'B3/S23',
          *flags,
          randpat = self.makesoup(rule, int(x), int(y)),
          soup_dims = '×'.join(dims.split('x'))
          )
    
    @sim.error
    async def sim_error(self, ctx, error):
        # In case of missing GEN:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'`Error: No {error.param.name.upper()} given. {self.moreinfo(ctx)}`')
        # Bad argument:
        elif isinstance(error, (commands.BadArgument, ZeroDivisionError)): # BadArgument on failure to convert to int, ZDE on gen=0
            badarg = str(error).split('"')[3].split('"')[0]
            await ctx.send(f'`Error: Invalid {badarg.upper()}. {self.moreinfo(ctx)}`')
        # Something went wrong in the command itself:
        elif isinstance(error, commands.CommandInvokeError):
            exc = traceback.format_exception(type(error), error, error.__traceback__)
            # extract relevant traceback only (not whatever led up to CommandInvokeError)
            end = '\nThe above exception was the direct cause of the following exception:\n\n'
            end = len(exc) - next(i for i, j in enumerate(reversed(exc), 1) if j == end)
            try:
                print('Ignoring exception in on_message', exc[0].split('"""')[1], *exc[1:end])
            except Exception as e:
                raise error
        else:
            raise error
        
    @mutils.command('Upload an asset (just ruletables for now)')
    async def upload(self, ctx):
        """
        # Attach a ruletable file to this command to have it be reviewed by Wright. #
        # If valid, it will be added to Caterer and be usable in !sim. #
        """
        msg = None
        attachment, *_ = ctx.message.attachments
        with io.BytesIO() as f:
            await attachment.save(f)
            temp = copy.copy(f)
            f.seek(0)
            msg = await self.bot.assets_chn.send(file=discord.File(temp, attachment.filename))
            emoji = '✅', '❌'
            [await msg.add_reaction(i) for i in emoji]
            def check(rxn, usr):
                return usr == self.bot.owner and rxn.message.id == msg.id and rxn.emoji in emoji
            rxn, usr = await self.bot.wait_for('reaction_add', check=check) # no timeout
            if rxn.emoji == '✅':
                query = '''
                INSERT INTO rules (
                  file, name, n_states, colors
                )
                SELECT $1::bytea, $2::text, $3::int, $4::text
                    ON CONFLICT (name)
                    DO UPDATE
                   SET file=$1::bytea, name=$2::text, n_states=$3::int, colors=$4::text
                '''
                await self.bot.pool.execute(query, f.read(), *mutils.extract_rule_info(f))
            return await msg.delete()   

def setup(bot):
    bot.add_cog(CA(bot))
