import discord
from discord.ext import commands
import re, os
import png, imageio
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from concurrent.futures import ProcessPoolExecutor
import struct
from collections import namedtuple

ColorScheme = namedtuple('ColorScheme', 'size table')
"""Color scheme used in the gif file.
ColorScheme is merely a container for these two things:
size: Contains a "color table size" that goes to the logical screen
      descriptor.
      **Note**
      The number of colors used in the gif file is: 2 ** (size + 1).
table: Contains a table of the 2**(size+1) colors. As you can see
       below, the colors are represented as RGB, each color in which
       occupying 1 byte (values 0-255.) The 3-byte colors are simply
       concatenated to make the color table.
       **Note**
       The last color is used as the borderline color in this script.
"""

colors = ColorScheme(size=1, table= (
    "\xFF\xFF\xFF" # State 0: white
    "\x00\x00\x00" # State 1: black
    "\x00\x00\x00" # (ignored)
    "\xC6\xC6\xC6" # Boundary: LifeWiki gray
    ))

# determines ~80% of available RAM to allow bgolly to use
maxmem = int(os.popen('free -m').read().split()[7]) // 1.25

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

def compress(data, mincodesize): #PASTED from scorbie/giffer.py
    """Apply lzw compression to the given data and minimum code size."""

    ncolors = 2**mincodesize
    cc, eoi = ncolors, ncolors + 1

    table = {chr(i): i for i in range(ncolors)}
    codesize = mincodesize + 1
    newcode = ncolors + 2

    outputbuff, outputbuffsize, output = cc, codesize, []

    databuff = ''

    for next in data:
        newbuff = databuff + next
        if newbuff in table:
            databuff = newbuff
        else:
            table[newbuff] = newcode
            newcode += 1
            # Prepend table[databuff] to outputbuff (bitstrings)
            outputbuff += table[databuff] << outputbuffsize
            outputbuffsize += codesize
            databuff = next
            if newcode > 2**codesize:
                if codesize < 12:
                    codesize += 1
                else:
                    # Prepend clear code.
                    outputbuff += cc << outputbuffsize
                    outputbuffsize += codesize
                    # Reset table
                    table = {chr(i): i for i in range(ncolors)}
                    newcode = ncolors + 2
                    codesize = mincodesize + 1
            while outputbuffsize >= 8:
                output.append(outputbuff & 255)
                outputbuff >>= 8
                outputbuffsize -= 8
    outputbuff += table[databuff] << outputbuffsize
    outputbuffsize += codesize
    while outputbuffsize >= 8:
        output.append(outputbuff & 255)
        outputbuff >>= 8
        outputbuffsize -= 8
    output.append(outputbuff)
    # Slice outputbuff into 255-byte chunks
    words = []
    for start in range(0, len(output), 255):
        end = min(len(output), start+255)
        words.append(''.join(map(chr, map(int, output[start:end]))))
    contents = [chr(mincodesize)]
    for word in words:
        contents.append(chr(len(word)))
        contents.append(word)
    contents.append('\x00')
    return ''.join(contents)

def straight_gif(current, patlist, positions, bbox, pad): #ADAPTED from scorbie/giffer.py

    assert len(patlist) == len(positions), (patlist, positions)
    xmin, ymin, width, height = bbox
    
    # Used in scaling up the frame size
    def scale_list(li, mult):
        """(li=[a, b, c], mult=2) => [a, a, b, b, c, c]
        Changes in one copy(ex. c) will affect the other (c)."""
        return [i for i in li for _ in range(mult)]
    
    header, trailer = 'GIF89a', '\x3b'
    screendesc = struct.pack("<2HB2b", width, height, 0x90+colors.size, 0, 0)
    applic = "\x21\xFF\x0B" + "NETSCAPE2.0" + struct.pack("<2bHb", 3, 1, 0, 0)
    imagedesc = "\x2C" + struct.pack("<4HB", 0, 0, width, height, 0x00)
    bordercolor = 2 ** (colors.size + 1) - 1
    borderrow = [bordercolor] * (width)
    # Gather contents to write as gif file.
    gifcontent = [header, screendesc, colors.table, applic]
    
    for index in range(len(patlist)):
        # Graphics control extension
        gifcontent += ["\x21\xF9", struct.pack("<bBH2b", 4, 0x00, pause, 0, 0)]
        
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
        
        anchor = min(width, height)
        mult = -(-75 // anchor) if anchor <= 75 else 1
        frame = scale_list([scale_list(row, mult) for row in frame], mult)
        
        image = ''.join(''.join(chr(i) for i in row) for row in frame)
        
        # Image descriptor + Image
        gifcontent += [imagedesc, compress(image, colors.size+1)]
        
    gifcontent.append(trailer)
    with open(f'{current}.gif','wb') as gif:
        gif.write("".join(gifcontent))

class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.loop = bot.loop
        self.executor = ProcessPoolExecutor() # this probably should not be in self's attributes but idk
        
    
    @commands.group(name='sim', invoke_without_subcommand=True)
    async def sim(self, ctx, gen: int, step: int = 1, rule='B3/S23', pat=None):
        if gen / step > 2500:
            await ctx.send(f"`Error: Cannot simulate more than 2500 frames. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
            return
    
        current = f'{self.dir}/{ctx.message.id}'
        
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
                await ctx.send(f"`Error: No PAT given and none found in channel history. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
                return
        await ctx.send(f'Running supplied pattern in rule `{rule}` with step `{step}` until generation `{gen}`.')
        
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat)
        
        # run bgolly with parameters
        os.system(f'{self.dir}/resources/bgolly -M {maxmem} -m {gen} -i {step} -r {rule} -o {current}_out.rle {current}_in.rle')
        
        # create gif on separate process to avoid blocking event loop
        patlist, positions, bbox = await self.loop.run_in_executor(self.executor, parse, current)
        assert len(patlist) == len(positions), (patlist, positions)
        xmin, ymin, width, height = bbox
        
        # Used in scaling up the frame size
        def scale_list(li, mult):
            """(li=[a, b, c], mult=2) => [a, a, b, b, c, c]
            Changes in one copy(ex. c) will affect the other (c)."""
            return [i for i in li for _ in range(mult)]
        
        header, trailer = 'GIF89a', '\x3b'
        screendesc = struct.pack("<2HB2b", width, height, 0x90+colors.size, 0, 0)
        applic = "\x21\xFF\x0B" + "NETSCAPE2.0" + struct.pack("<2bHb", 3, 1, 0, 0)
        imagedesc = "\x2C" + struct.pack("<4HB", 0, 0, width, height, 0x00)
        bordercolor = 2 ** (colors.size + 1) - 1
        borderrow = [bordercolor] * (width)
        # Gather contents to write as gif file.
        gifcontent = [header, screendesc, colors.table, applic]
        
        for index in range(len(patlist)):
            # Graphics control extension
            gifcontent += ["\x21\xF9", struct.pack("<bBH2b", 4, 0x00, pause, 0, 0)]
            
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
            
            anchor = min(width, height)
            mult = -(-75 // anchor) if anchor <= 75 else 1
            frame = scale_list([scale_list(row, mult) for row in frame], mult)
            
            image = ''.join(''.join(chr(i) for i in row) for row in frame)
            
            # Image descriptor + Image
            gifcontent += [imagedesc, compress(image, colors.size+1)]
            
        gifcontent.append(trailer)
        with open(f'{current}.gif','wb') as gif:
            gif.write("".join(gifcontent))
            
        await ctx.send(file=discord.File(f'{current}.gif'))
        os.remove(f'{current}.gif')
    
    @sim.error
    async def sim_error(self, ctx, error):
        # In case of missing GEN:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"`Error: No {error.param.upper()} given. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
        

def setup(bot):
    bot.add_cog(CA(bot))
