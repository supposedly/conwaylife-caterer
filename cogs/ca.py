import discord
from discord.ext import commands
import re, os
import png, imageio
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from concurrent.futures import ProcessPoolExecutor

# matches multiline XRLE
rxrle = re.compile(r'^(?:#.*$)?(?:^x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?)?\n(^[\dob$]*[ob$][\dob$\n]*!?)$', re.M)

# splits RLE into its runs
rruns = re.compile(r'([0-9]*)([ob])') # [rruns.sub(lambda m:''.join(['0' if m.group(2) == 'b' else '1' for x in range(int(m.group(1)) if m.group(1) else 1)]), pattern) for pattern in patlist[i]]

# unrolls $ signs
rdollarsigns = re.compile(r'(\d+)\$')

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
        dx, dy = xpos - xmin, ypos - ymin
        
        # Create a blank frame of off cells
        # Colors: on=0, off=1
        frame = [[1] * width for _ in range(height)]
        
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

def makegif(current, gen):
    # finally, pass all created pics to imageio for conversion to gif
    # then either upload to gfycat or send directly to discord depending on presence of "g" flag
    png_dir = f'{current}_frames/'
    for subdir, dirs, files in os.walk(png_dir):
        files.sort()
        with imageio.get_writer(f'{current}.gif', mode='I', duration=str(-0.5 / (-gen // 10))) as writer:
            for file in files:
                file_path = os.path.join(subdir, file)
                writer.append_data(imageio.imread(file_path))
    os.system(f'rm -r {png_dir}')


class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.loop = bot.loop
        self.executor = ProcessPoolExecutor() # this probably should not be in self's attributes but idk
    
    @commands.command(name='sim')
    async def sim(self, ctx, gen, step='1', rule='B3/S23', pat=None, flags=None): # flags = *g*t
        current = f'{self.dir}/{ctx.message.id}'
        os.mkdir(f'{current}_frames')
        
        if pat is None:
            async for msg in ctx.channel.history(limit=50):
                try:
                    rmatch = list(filter(None, [rxrle.match(i) for i in msg.content.split('`')]))[0]
                except IndexError as e:
                    print(e)
                else:
                    pat = rmatch.group(2)
                    if rmatch.group(1):
                        rule = rmatch.group(1)
                    break
            if pat is None: # stupid
                await ctx.send(f"`Error: No PAT given and none found in channel history. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
                return
        await ctx.send(f'Running supplied pattern in rule `{rule}` with step `{step}` until generation `{gen}`.')
        
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat)
        
        # run bgolly with parameters
        os.system(f'{self.dir}/resources/bgolly -m {gen} -i {step} -r {rule} -o {current}_out.rle {current}_in.rle')
        
        # create gif on separate process to avoid blocking event loop
        patlist, positions, bbox = await self.loop.run_in_executor(self.executor, parse, current)
        await self.loop.run_in_executor(self.executor, makeframes, current, patlist, positions, bbox, len(str(gen)))
        await self.loop.run_in_executor(self.executor, makegif, current, int(gen))
        
        await ctx.send(file=discord.File(f'{current}.gif'))
        os.remove(f'{current}.gif')
    
    @sim.error
    async def sim_error(self, ctx, error):
        # In case of missing GEN:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"`Error: No {error.param.upper()} given. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
        

def setup(bot):
    bot.add_cog(CA(bot))
