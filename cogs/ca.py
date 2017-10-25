import discord
from discord.ext import commands
import re
import os

# jesus christ i am sorry (matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring)
rrulestring = re.compile(r'^(B)?[0-8cekainyqjrtwz-]*/(?(1)S?[0-8cekainyqjrtwz\-]*|[0-8cekainyqjrtwz\-]*(?:/[\d]{1,3})?)$') 

# matches one-line RLE or .lif
rpattern = re.compile(r'^[\dobo$]*[obo$][\dobo$]*!?$|^[.*!]+$')

# matches multiline XRLE
rxrle = re.compile(r'^#.*$|^x ?= ?\d+, ?y ?= ?\d+, ?rule ?= ?(.+)$|^[\dobo$]*[obo$][\dobo$]*!?$', re.M)

# matches .lif
rlif = re.compile(r'(?:^[.*!]+$)+')


# runs of dots/stars
rruns = re.compile(r'([0-9]+)([ob])') # compile.sub(lambda m:''.join(['.' if m.group(2) == 'b' else '*' for x in range(int(m.group(1)))]), rle)

# single dots/stars
rsingletons = re.compile(r'(?<![0-9])[ob]') # singletons.sub(lambda m:'.' if m.group() == 'b' else '*', rle)

# exclamation points
exclm = re.compile(r'([0-3]*)\$') # exclm.sub(lambda m:'!' if m.group(1) == '' else ''.join(['!' for x in range(int(m.group(1)))]), rle)


# ---- #


class CA:
    def __init__(self, bot):
        self.bot = bot
        #TODO: Log channel messages at startup then continue to log with on_message() to avoid slowness when !sim is called
        # maybe
            
    
    @commands.command(name='sim')
    async def sim(self, ctx, *args): #args: *RULE *PAT GEN *STEP *g
        gfy = False
        if 'g' in args:
            args.pop(args.index('g'))
            gfy = True
        if len(args) > 4:
            await ctx.send(f'`Error: Too many args. "{self.bot.command_prefix(self.bot, ctx.message)}help sim" for more info`')
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
                await ctx.send('`Error: No pattern specified and none found in channel history.`')
                return
        await ctx.send('Running supplied pattern in rule `{0[rule]}` with step `{0[step]}` until generation `{0[gen]}`.'.format(parse))
        
        with open(f'{ctx.message.id}_in.rle', 'w') as patfile:
            patfile.write(parse["pat"])
        
        os.system('{0}/resources/bgolly -m {1[gen]} -i {1[step]} -q -q -r {1[rule]} -o {2}_out.rle {2}_in.rle'.format(os.path.dirname(__file__), parse, ctx.message.id))
        # From here:
        # readlines on bgolly's output file and divide resulting list into two - one with each individual RLE and one with corresponding (width, height)
        # for pattern in rle_list: turn into .lif file with final regexes above
        # . . . then pass to PIL for conversion to image
        # finally pass all created pics to imageio for conversion to gif
        # then either upload to gfycat or send directly to discord depending on presence of "g" flag
        # g'luck
                

def setup(bot):
    bot.add_cog(CA(bot))
