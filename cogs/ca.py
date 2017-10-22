import discord
from discord.ext import commands
import re

rrulestring = re.compile('^(B)?[\dcekainyqjrtwz-]*/(?(1)S[\dcekainyqjrtwz\-]*|[\dcekainyqjrtwz\-]*/?[\dcekainyqjrtwz\-]*)$') #jesus christ i am sorry (matches B/S and if no B then either 2-state single-slash rulestring or generations rulestring)
rpattern = re.compile('') #matches one-line RLE

class CA:
    def __init__(self, bot)
        self.bot = bot
    
    @commands.command(name='sim')
    def sim(self, ctx, *args) #args: *RULE *PAT *STEP GEN

def setup(bot):
    bot.add_cog(CA(bot))
