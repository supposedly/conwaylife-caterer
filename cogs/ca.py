import discord
from discord.ext import commands
import re
import os

# jesus christ i am sorry (matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring)
rrulestring = re.compile(r'^(B)?[0-8cekainyqjrtwz-]*/(?(1)S?[0-8cekainyqjrtwz\-]*|[0-8cekainyqjrtwz\-]*(?:/[\d]{1,3})?)$') 

# matches one-line RLE or .lif
rpattern = re.compile(r'^[\dobo$]*[obo$][\dobo$]*!?$|^[.*!]+$')

# matches multiline XRLE
rxrle = re.compile(r'^(?:#.*$)?(?:^x ?= ?\d+, ?y ?= ?\d+, ?rule ?= ?(.+)$)?\n(^[\dobo$]*[obo$][\dobo$]*!?)$', re.M)

# matches .lif
rlif = re.compile(r'(?:^[.*!]+$)+')


# runs of dots/stars
rruns = re.compile(r'([0-9]+)([ob])') # rruns.sub(lambda m:''.join(['.' if m.group(2) == 'b' else '*' for x in range(int(m.group(1)))]), rle)

# single dots/stars
rsingletons = re.compile(r'(?<![0-9])[ob]') # singletons.sub(lambda m:'.' if m.group() == 'b' else '*', rle)

# exclamation points
rexclm = re.compile(r'([0-3]*)\$') # exclm.sub(lambda m:'!' if m.group(1) == '' else ''.join(['!' for x in range(int(m.group(1)))]), rle)


# ---- #


class CA:
    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.dirname(os.path.abspath(__file__))
        #TODO: Log channel messages at startup then continue to log with on_message() to avoid slowness when !sim is called
        # maybe
            
    
    @commands.command(name='sim')
    async def sim(self, ctx, *args): #args: *RULE *PAT GEN *STEP *g
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
                rmatch = rxrle.match(msg.content)
                if rmatch:
                    parse["pat"] = rmatch.group(2)
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
        
        with open(f'{ctx.message.id}_in.rle', 'w') as pat:
            pat.write(parse["pat"])
        
        filedir = os.path.dirname(os.path.abspath(f'{ctx.message.id}_in.rle'))
        
        os.system('{0}/resources/bgolly -m {1[gen]} -i {1[step]} -q -q -r {1[rule]} -o {0}/{2}_out.rle {3}/{2}_in.rle'.format(self.dir, parse, ctx.message.id, filedir))
        # From here:
        # readlines on bgolly's output file and divide resulting list into two - one with each individual RLE and one with corresponding (width, height)
        with open(f'{self.dir}/{ctx.message.id}_out.rle', 'r') as pat:
            patlist = [line.rstrip('\n') for line in pat]
        
        headers = patlist[::2] # just headers
        headers = [tuple(map(int, header[4:header.find(', r')].split(', y = '))) for header in headers] # remove rulestring (not needed) and convert x, y to tuple of ints
        headers = [(x, y, x * y) for x, y in headers] # put total area in tuple[2]
        
        patlist = patlist[1::2] # just RLE
        patlist = [pattern[:pattern.find('!')] for pattern in patlist] # remove final newline and exclamation point
        
        # applies above regexes to turn RLE into .lif ... readable enough if second arg recursively unpacked
        patlist = [rexclm.sub(lambda m:'!' if m.group(1) == '' else ''.join(['!' for x in range(int(m.group(1)))]), rsingletons.sub(lambda m:'.' if m.group() == 'b' else '*', rruns.sub(lambda m:''.join(['.' if m.group(2) == 'b' else '*' for x in range(int(m.group(1)))]), pattern))) for pattern in patlist]
        
        print(patlist)
        
        # finally pass all created pics to imageio for conversion to gif
        # then either upload to gfycat or send directly to discord depending on presence of "g" flag
        # g'luck
                

def setup(bot):
    bot.add_cog(CA(bot))
