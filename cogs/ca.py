import discord
from discord.ext import commands
import re, os
import png, imageio
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

# jesus christ i am sorry (matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring)
rrulestring = re.compile(r'^(B)?[0-8cekainyqjrtwz-]*/(?(1)S?[0-8cekainyqjrtwz\-]*|[0-8cekainyqjrtwz\-]*(?:/[\d]{1,3})?)$') 

# matches one-line RLE or .lif
rpattern = re.compile(r'^[\dobo$]*[obo$][\dobo$]*!?$|^[.*!]+$')

# matches multiline XRLE
rxrle = re.compile(r'^(?:#.*$)?(?:^x ?= ?\d+, ?y ?= ?\d+, ?rule ?= ?(.+)$)?\n(^[\dobo$]*[obo$][\dobo$\n]*!?)$', re.M)

# splits RLE into its runs
rruns = re.compile(r'([0-9]*)([ob])') # [rruns.sub(lambda m:''.join(['0' if m.group(2) == 'b' else '1' for x in range(int(m.group(1)) if m.group(1) else 1)]), pattern) for pattern in patlist[i]]

# unrolls $ signs
rdollarsigns = re.compile(r'(\d+)\$')

# matches .lif
rlif = re.compile(r'(?:^[.*!]+$)+')


# ---- #


class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        #TODO: Log channel messages at startup then continue to log with on_message() to avoid slowness when !sim is called
        # maybe
            
    
    @commands.command(name='sim')
    async def sim(self, ctx, *args): #args: *RULE *PAT GEN *STEP *g
        os.mkdir(f'{self.dir}/{ctx.message.id}_frames')
        gfy = False
        if 'g' in args:
            args.pop(args.index('g'))
            gfy = True
        if len(args) > 4:
            await ctx.send(f"`Error: Too many args. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
            return
        parse = {"rule": 'B3/S23', "pat": None, "gen": None, "step": '1'}
        for item in args:
            if item.isdigit():
                parse["step" if parse["gen"] else "gen"] = item
            elif rpattern.match(item):
                parse["pat"] = item
            elif rrulestring.match(item):
                parse["rule"] = item
        if parse["gen"] is None:
            await ctx.send('`Error: No GEN specified.`')
            return
        if parse["pat"] is None:
            async for msg in ctx.channel.history(limit=50): #TODO from above: Log channel messages at startup then continue to log with on_message() to avoid slowness when !sim is called
                rmatch = rxrle.match(msg.content.lstrip('`').rstrip('`'))
                if rmatch:
                    parse["pat"] = rmatch.group(2).replace('\n', '')
                    try:
                        parse["rule"] = rmatch.group(1)
                    except Exception as e:
                        pass
                    break
                    
                rmatch = rlif.match(msg.content)
                if rmatch:
                    parse["pat"] = rmatch.group(0)
                    break
            if parse["pat"] is None: #stupid
                await ctx.send(f"`Error: No PAT given and none found in channel history. '{self.bot.command_prefix(self.bot, ctx.message)}help sim' for more info`")
                return
        await ctx.send('Running supplied pattern in rule `{0[rule]}` with step `{0[step]}` until generation `{0[gen]}`.'.format(parse))
        
        with open(f'{self.dir}/{ctx.message.id}_in.rle', 'w') as pat:
            pat.write(parse["pat"])
        
        os.system('{0}/resources/bgolly -m {1[gen]} -i {1[step]} -q -q -r {1[rule]} -o {0}/{2}_out.rle {0}/{2}_in.rle'.format(self.dir, parse, ctx.message.id))
        # From here:
        # readlines on bgolly's output file and divide resulting list into two - one with each individual RLE and one with corresponding (width, height)
        with open(f'{self.dir}/{ctx.message.id}_out.rle', 'r') as pat:
            patlist = [line.rstrip('\n') for line in pat]

        os.remove(f'{self.dir}/{ctx.message.id}_out.rle')
        os.remove(f'{self.dir}/{ctx.message.id}_in.rle')
        
        positions = patlist[::3]
        positions = [eval(i) for i in positions]
        
        bboxes = patlist[1::3] # just bounding boxes
        bboxes = [eval(i) for i in bboxes]
        
        maxwidth = max(bboxes)[0]
        maxheight = max(bboxes, key=lambda x:x[1])[1]
        
        patlist = patlist[2::3] # just RLE
        # ['4b3$o', '3o2b'] -> ['4b$$$o', '3o2b']
        patlist = [rdollarsigns.sub(lambda m: ''.join(['$' for i in range(int(m.group(1)))]), j).replace('!', '') for j in patlist] # unroll newlines
        # ['4b$$$o', '3o2b'] -> [['4b', '', '', '', 'o'], ['3o', '2b']]
        patlist = [i.split('$') for i in patlist]

        pad = len(str(parse["gen"])) # what to pad number out to

        for index in range(len(patlist)):
            # unroll RLE and convert to list of ints, 1=off and 0=on, then lastly pad out to proper width
            frame = [l+[1]*((maxwidth - len(l)) + positions[index][0]) for l in [list(map(int, i)) for i in [rruns.sub(lambda m:''.join(['1' if m.group(2) == 'b' else '0' for x in range(int(m.group(1)) if m.group(1) else 1)]), pattern) for pattern in patlist[index]]]]
            
            # pad out to proper height with 1=off cell
            [frame.append([0]*maxwidth) for j in range((maxheight - len(frame)) + positions[index][1])]
            
            # double frame size, need to find a better way than nested list comp to do this haha
            frame = [[[frame[i][j//2] for j in range(len(frame[i])*2)] for i in range(len(frame))][k//2] for k in range(len(frame)*2)]
            
            with open(f'{self.dir}/{ctx.message.id}_frames/{index:0{pad}}.png', 'wb') as out:
                w = png.Writer(len(frame[0]), len(frame), greyscale=True, bitdepth=1)
                w.write(out, frame)
        
        # finally pass all created pics to imageio for conversion to gif

        png_dir = f'{self.dir}/{ctx.message.id}_frames/'
        for subdir, dirs, files in os.walk(png_dir):
            files.sort()
            with imageio.get_writer(f'{self.dir}/{ctx.message.id}.gif', mode='I', duration=str(-0.5 / (-int(parse["gen"]) // 10))) as writer:
                for file in files:
                    file_path = os.path.join(subdir, file)
                    writer.append_data(imageio.imread(file_path))
        os.system(f'rm -r {png_dir}')
        
        # then either upload to gfycat or send directly to discord depending on presence of "g" flag
        await ctx.send(file=discord.File(f'{self.dir}/{ctx.message.id}.gif'))
        os.remove(f'{self.dir}/{ctx.message.id}.gif')
        # g'luck
                

def setup(bot):
    bot.add_cog(CA(bot))
