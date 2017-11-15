import discord
import png, imageio
import re, os, sys, traceback
import random, math
from discord.ext import commands
from cogs.resources import cmd
from concurrent.futures import ProcessPoolExecutor

from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

# matches LtL rulestring
rLtL = re.compile(r'R\d{1,3},C\d{1,3},M[01],S\d+\.\.\d+,B\d+\.\.\d+,N[NM]')

# jesus christ i am sorry (matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring)
rrulestring = re.compile(r'(B)?[0-8cekainyqjrtwz-]+(?(1)/?(S)?[0-8cekainyqjrtwz\-]*|/(S)?[0-8cekainyqjrtwz\-]*(?(2)|(?(3)|/[\d]{1,3})?))')

# matches multiline XRLE
rxrle = re.compile(r'^(?:#.*$)?(?:^x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?)?\n(^[\dob$]*[ob$][\dob$\n]*!?)$', re.M)

# splits RLE into its runs
rruns = re.compile(r'([0-9]*)([ob])') # [rruns.sub(lambda m:''.join(['0' if m.group(2) == 'b' else '1' for x in range(int(m.group(1)) if m.group(1) else 1)]), pattern) for pattern in patlist[i]]

# unrolls $ signs
rdollarsigns = re.compile(r'(\d+)\$')

# determines 80% of available RAM to allow bgolly to use
maxmem = int(os.popen('free -m').read().split()[7]) // 1.25

# ---- #

def parse(current):
    with open(f'{current}_out.rle', 'r') as pat:
        patlist = [line.rstrip('\n') for line in pat]

    os.remove(f'{current}_out.rle')
    os.remove(f'{current}_in.rle')
    
    positions = patlist[::3]
    positions = [eval(i) for i in positions]
    
    bboxes = patlist[1::3] # just bounding boxes
    bboxes = [eval(i) for i in bboxes]
    
    # Determine the bounding box to make gifs from
    # The rectangle: xmin <= x <= xmax, ymin <= y <= ymax
    # where (x|y)(min|max) is the min/max coordinate across all gens.
    xmins, ymins = zip(*positions)
    widths, heights = zip(*bboxes)
    xmaxs = [xm+w for xm, w in zip(xmins, widths)]
    ymaxs = [ym+h for ym, h in zip(ymins, heights)]
    xmin, ymin, xmax, ymax = min(xmins), min(ymins), max(xmaxs), max(ymaxs)
    # Bounding box: top-left x and y, width and height
    bbox = xmin, ymin, xmax-xmin, ymax-ymin
    
    patlist = patlist[2::3] # just RLE
    # ['4b3$o', '3o2b'] -> ['4b$$$o', '3o2b']
    patlist = [rdollarsigns.sub(lambda m: ''.join(['$' for i in range(int(m.group(1)))]), j).replace('!', '') for j in patlist] # unroll newlines
    # ['4b$$$o', '3o2b'] -> [['4b', '', '', '', 'o'], ['3o', '2b']]
    patlist = [i.split('$') for i in patlist]
    return patlist, positions, bbox

def makeframes(current, patlist, positions, bbox, pad):
    
    assert len(patlist) == len(positions), (patlist, positions)
    xmin, ymin, width, height = bbox
    
    # Used in doubling the frame size
    def scale_list(li, mult):
        """(li=[a, b, c], mult=2) => [a, a, b, b, c, c]
        Changes in one copy(ex. c) will affect the other (c)."""
        return [i for i in li for _ in range(mult)]
    
    for index in range(len(patlist)):
        pat = patlist[index]
        xpos, ypos = positions[index]
        dx, dy = (xpos - xmin) + 1, (ypos - ymin) + 1 #+1 for one-cell padding
        
        # Create a blank frame of off cells
        # Colors: on=0, off=1
        frame = [[1] * (width+2) for _ in range(height+2)] #+2 for one-cell padding
        
        # unroll RLE and convert to list of ints, 1=off and 0=on
        int_pattern = []
        for row in pat:
            int_row = []
            for runs, chars in rruns.findall(row):
                runs = int(runs) if runs else 1
                state = 1 if chars == 'b' else 0
                int_row.extend([state] * runs)
            int_pattern.append(int_row)
        
        # Draw the pattern onto the frame
        for i, int_row in enumerate(int_pattern):
            # replace this row of frame with int_row
            frame[dy+i][dx:dx+len(int_row)] = int_row
        
        anchor = min(height, width)
        mult = -(-75 // anchor) if anchor <= 75 else 1
        frame = scale_list([scale_list(row, mult) for row in frame], mult)
        
        with open(f'{current}_frames/{index:0{pad}}.png', 'wb') as out:
            w = png.Writer(len(frame[0]), len(frame), greyscale=True, bitdepth=1)
            w.write(out, frame)    

def makegif(current, gen, step):
    # finally, pass all created pics to imageio for conversion to gif
    # then either upload to gfycat or send directly to discord depending on presence of "g" flag
    png_dir = f'{current}_frames/'
    for subdir, dirs, files in os.walk(png_dir):
        files.sort()
        with imageio.get_writer(f'{current}.gif', mode='I', duration=str(max(1/60, (-0.5 / (-gen // 10)) / step))) as writer:
            for file in files:
                file_path = os.path.join(subdir, file)
                writer.append_data(imageio.imread(file_path))
    os.system(f'rm -r {png_dir}')

def makesoup(rulestring, x, y):
    """generates random soup as RLE with specified dimensions"""

    rle = f'x = {x}, y = {y}, rule = {rulestring}\n'
    
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


class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.loop = bot.loop
        self.executor = ProcessPoolExecutor() # this probably should not be in self's attributes but idk
    
    @commands.group(name='sim', aliases=cmd.aliases['sim'], invoke_without_command=True)
    async def sim(self, ctx, gen: int, step: int=1, rule='B3/S23', pat=None, **kwargs):
        rand = kwargs.pop('randpat', None)
        dims = kwargs.pop('soup_dims', None)
        
        if gen / step > 2500:
            return await ctx.send(f"`Error: Cannot simulate more than 2500 frames. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
    
        current = f'{self.dir}/{ctx.message.id}'
        os.mkdir(f'{current}_frames')
        
        if rand:
            pat = rand
            rand = f'Running `{dims}` soup in rule `{rule}` with step `{step}` until generation `{gen}`.' # meh
        if pat is None:
            async for msg in ctx.channel.history(limit=50):
                try:
                    rmatch = list(filter(None, [rxrle.match(i) for i in msg.content.split('`')]))[0]
                except IndexError as e:
                    pass
                else:
                    pat = rmatch.group(2)
                    if rmatch.group(1):
                        rule = rmatch.group(1)
                    break
            if pat is None: # stupid
                return await ctx.send(f"`Error: No PAT given and none found in channel history. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
        await ctx.send(rand if rand else f'Running supplied pattern in rule `{rule}` with step `{step}` until generation `{gen}`.')
        
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat)
        
        # run bgolly with parameters
        preface = f'{self.dir}/resources/bgolly' + (' -a "Larger than Life"' if rLtL.match(rule) else '')
        bg_err = os.popen(f'{preface} -m {gen} -i {step} -r {rule} -o {current}_out.rle {current}_in.rle').read()
        if bg_err:
            return await ctx.send(f'`{bg_err}`')
        
        # create gif on separate process to avoid blocking event loop
        patlist, positions, bbox = await self.loop.run_in_executor(self.executor, parse, current)
        await self.loop.run_in_executor(self.executor, makeframes, current, patlist, positions, bbox, len(str(gen)))
        await self.loop.run_in_executor(self.executor, makegif, current, gen, step)
        
        await ctx.send(file=discord.File(f'{current}.gif'))
        os.remove(f'{current}.gif')
        
    @sim.command(name='rand', aliases=cmd.aliases['sim.rand'])
    async def rand(self, ctx, x='', y='', gen='', rule='', step: int=1):
        moreinfo = f"'{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info"
        
        #XXX: below seems a bit more long-winded than is necessary
        
        if x and (y and not y.isdigit()): # allow user to specify only gen and rule and maybe step, defaulting to xy 16 x 16
            if gen.isdigit():
                step = int(gen)
            gen, rule = x, y
            x, y = 16, 16
        elif x and not y: # allow user to specify only gen, defaulting to xy 16 x 16 and rule last sent or B3/S23
            gen, x, y = x, 16, 16
        elif x and y.isdigit() and not gen:
            gen, step = x, int(y)
            x, y = 16, 16
        if rule.isdigit(): # allow user to specify only dims, gen, and step, defaulting to rule last sent or B3/S23
            step, rule = int(rule), ''
        if not rule:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rLtL.search(msg.content) or rrulestring.search(msg.content)
                if rmatch:
                    rule = rmatch.group()
                    break
            if not rule: # stupid
                rule = 'B3/S23'
        await ctx.invoke(self.sim, gen=int(gen), rule=rule, step=step, randpat=makesoup(rule, int(x), int(y)), soup_dims='×'.join(str(i) for i in (x,y)))
    
    @sim.error
    async def sim_error(self, ctx, error):
        moreinfo = f"'{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`"
        # In case of missing GEN:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'`Error: No {error.param.upper()} given. {moreinfo}')
        # Bad argument:
        elif isinstance(error, (commands.BadArgument, ZeroDivisionError)): # BadArgument on failure to convert to int, ZDE on gen=0
            badarg = str(error).split('"')[3].split('"')[0]
            await ctx.send(f'`Error: Invalid {badarg.upper()}. {moreinfo}')
        # Something went wrong in the command itself:
        elif isinstance(error, commands.CommandInvokeError):
            exc = traceback.format_exception(type(error), error, error.__traceback__)
            
            # extract relevant traceback only (not whatever led up to CommandInvokeError)
            end = '\nThe above exception was the direct cause of the following exception:\n\n'
            end = len(exc) - next(i for i, j in enumerate(reversed(exc), 1) if j == end)
            
            try:
                print('Ignoring exception in on_message', exc[0].split('"""')[1], *exc[1:end])
            except Exception as e:
                print(f'{e.__class__.__name__}: {e}\n\n')
                raise error
        else:
            raise error
        
        

def setup(bot):
    bot.add_cog(CA(bot))
