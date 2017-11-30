import discord
from discord.ext import commands
from PIL import Image
import os, asyncio, io
import concurrent.futures
import collections
import codecs, unicodedata
import re, fileinput

# IMPORTANT: Make sure you NEVER change the name of the below variable.
# This is because the `edit ESC` and `edit rESC` commands are given the
# ability to edit this file's source in order to update this variable, 
# and to do that effectively they must of course be able to find it
# first by this name.

# Note: ZWSP works nicely, being an invisible character that for
# some reason, unlike its fellow whitespace characters, is left
# unstripped by Discord.

ESC = '\u200b' # ZERO WIDTH SPACE '​'

class SList(list):
  """
  Implements list "subtraction" (i.e. literally just using - operator to filter one list from another)
  Type of left-hand operand (i.e. the minuend) determines return type
  """
  def __init__(self, *items): # the * is to allow SList(1,2,3) => [1, 2, 3]
    if len(items) == 1 and isinstance(items[0], collections.Iterable): # isinstance() is to allow, say, SList(5) to return [5] instead of raising TypeError: not iterable
        [items] = items # unpack
    super().__init__(items)
    
  def __sub__(self, other): # SList()-other
    return self.__class__(i for i in self if i not in other)
    
  def __rsub__(self, other): # other-SList()
    try:
      return other.__class__(i for i in other if i not in self)
    except TypeError as e: # if 'other' is of a non-instantiable type, like generator, that can still be iterated through
      return self.__class__(other) # Not sure whether to do this or just let it raise TypeError


class ColorConvert(commands.ColourConverter):
    """Equivalent to commands.ColourConverter, but adds certain emoji (as defined in self.colors)"""
    def __init__(self):
        super().__init__()
        self.default_colors = {
          'teal': 0x1abc9c,
          'green': 0x2ecc71,
          'blue': 0x3498db,
          'purple': 0x9b59b6,
          'magenta': 0xe91e63,
          'gold': 0xc27c0e,
          'orange': 0xe67e22,
          'red': 0xe74c3c,
          'blurple': 0x7289da,
          'greyple': 0x99aab5,
          'lighter grey': 0x95a5a6,
          'darker grey': 0x546e7a
          }          
        self.default_colors_dark = {
          'dark teal': 0x11806a,
          'dark green': 0x1f8b4c,
          'dark blue': 0x206694,
          'dark purple': 0x71368a,
          'dark magenta': 0xad1457,
          'dark gold': 0xc27c0e,
          'dark orange': 0xa84300,
          'dark red': 0x992d22,
          'dark grey': 0x607d8b
          }
        self.light_colors = {
          'light teal': 0x56bafd,
          'light green': 0x4cea8f,
          'light blue': 0x52b6f9,
          'light purple': 0xb981d4,
          'light magenta': 0xfd3277,
          'light gold': 0xe09a2c,
          'light orange': 0xfa9236,
          'light red': 0xfb6050,
          'light grey': 0x979c9f
          }
        self.emote_colors = {
          '✖':0,
          '❤':12458289,
          '💛':16632664,
          '💚':7909721,
          '💙':6139372,
          '💜':11177686,
          '⚪':16777215,
          '⚫':65793
          }
    async def convert(self, ctx, argument, ret=False):
        try:
            color = await super().convert(ctx, argument)
        except commands.errors.BadArgument as e:
            try:
                color = discord.Colour(self.light_colors.get(argument, None) or self.emote_colors[argument])
            except (KeyError, ValueError) as e:
                if ret:
                    color = None
                else:
                    raise
        if ret:
            return color, argument.split()
        return color


class TouchableRole(commands.RoleConverter):
    """Really just an abstraction layer between regular role names and role names prepended with the ESC character"""
    @staticmethod
    def namecheck(ctx, rolename):
        if rolename.startswith(' ') and ctx.message.author is ctx.guild.owner:
            return rolename[1:]
        return f'{ESC}{rolename}'
    async def convert(self, ctx, rolename):
        return await super().convert(ctx, self.namecheck(ctx, rolename))
    async def create(self, ctx, rolename, color, reason):
        return await ctx.guild.create_role(name=self.namecheck(ctx, rolename), color=color, reason=reason)


def is_owner():
    async def predicate(ctx):
        return ctx.author is ctx.guild.owner
    return commands.check(predicate)


@commands.check
def block_outside_lounge(ctx):
    return ctx.guild.id == 357922255553953794


class RoleManagement:
    def __init__(self, bot):
        self.bot = bot
        self.colors = ColorConvert().emote_colors
    
    def ESC_decode(argument):
        return codecs.decode(argument, 'unicode_escape')
    
    def edit_ESC_var(self, newvar):
        global ESC; ESC = newvar
        for line in fileinput.input(__file__, inplace=True):
            if line.startswith('ESC'):
                print(f'ESC =', r"'\u{:0>4}'".format(hex(ord(newvar))[2:]), f"# {unicodedata.name(newvar)} '{newvar}'")
            else:
                print(line.rstrip('\n'))
    
    async def auto_convert(self, ctx, args):
        color, name = await ColorConvert().convert(ctx, args[0], True)
        if color is None:
            color, name = await ColorConvert().convert(ctx, ' '.join(args[:2]), True)
        return (color, ' '.join(args if color is None else args-SList(name)))
    
    async def check_role(self, role, member):
        if not role.members - SList(member):
            await role.delete(reason=f'Memberless role; deleted by {self.bot.user.name} (bot)',)
    
    async def add_role(self, ctx, member, role):
        ext_roles = [i for i in member.roles if i.name.startswith(ESC)]
        for ext_role in ext_roles:
            await member.remove_roles(ext_role, reason=f'Member took new role; by {self.bot.user.name} (bot)')
            await self.check_role(ext_role, member)
        await member.add_roles(role, reason=f'Via {self.bot.user.name} (bot)')
    
    async def prompt_color(self, ctx, prompt):
        await prompt.edit(content='Pick a color or type one out! Choose ✖ for default color.')
        [await prompt.add_reaction(color_emote) for color_emote in self.colors]
        
        futures = [
          self.bot.wait_for('message', timeout=15.0, check=lambda msg: msg.author == ctx.message.author),
          self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in self.colors and rxn.message.id == prompt.id and usr is ctx.message.author)
          ]
        
        resp = await asyncio.wait(futures, loop=self.bot.loop, timeout=15.0, return_when=concurrent.futures.FIRST_COMPLETED) # returns two sets, Finished and Pending
        try:
            [resp] = resp[0] # unpack sole value of Finished set (will only have one value bc only one of the two coros can finish first)
        except ValueError as e: # if neither task completed then there will be nothing in the Finished set
            await prompt.delete()
            raise
        else:
            await prompt.clear_reactions()
            resp = resp.result()
            return await ColorConvert().convert(ctx, resp.content if isinstance(resp, discord.Message) else resp[0].emoji)
    
    @commands.group(name='role',invoke_without_command=True,)
    async def role(self, ctx, *args):
        color, rolename = await self.auto_convert(ctx, args)
        args = ' '.join(args)
        async def make_role(rolename, color, say=ctx.send, reason=f'Via {self.bot.user.name} (bot) by {ctx.message.author.name}'):
            role = await TouchableRole().create(ctx, rolename, color=color, reason=reason)
            await say(content=f'Successfully created role `{rolename}` with color `{str(color)[1:]}`!')
            return role
        if not rolename:
            rolename = args
        try:
            role = await TouchableRole().convert(ctx, rolename)
            # The above would have raised an exception, preventing us
            # from getting to here, if the role didn't exist; now that
            # we know it exists, though, we can check to see if the
            # user requested a color and if so whether it conflicts
            # with the preexisting role's color.
            if color is not None and color.value != role.color.value:
                rxns = ('✅', '❌')
                prompt = await ctx.send(f'Role `{rolename}` already exists, but with color `{str(role.color)[1:]}`. Still want it?')
                [await prompt.add_reaction(i) for i in rxns]
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in rxns and rxn.message.id == prompt.id and usr is ctx.message.author)
                except asyncio.TimeoutError as e:
                    return await prompt.delete()
                else:
                    await prompt.clear_reactions()
                if reaction.emoji == '❌':
                    return await prompt.delete()
        except commands.errors.BadArgument as e:
            ext_colors = {i.color.value: i for i in ctx.guild.roles if i.name.startswith(ESC)}
            if color is not None and color.value in ext_colors:
                role = ext_colors[color.value]
                await ctx.send(f'Assigning existing role `{role.name}` for color `{str(color)[1:]}`.')
            elif color is not None:
                rxns = ('✅', '🔴', '❌')
                msg = f'Create role `{rolename}` with color `{str(color)[1:]}`?\n(Red dot to create '
                msg += ('this role' if rolename == args else f'role `{args}`') + 'with custom color)'
                prompt = await ctx.send(msg)
                [await prompt.add_reaction(i) for i in rxns]
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in rxns and rxn.message.id == prompt.id and usr is ctx.message.author)
                except asyncio.TimeoutError as e:
                    return await prompt.delete()
                else:
                    await prompt.clear_reactions()
                if reaction.emoji == '❌':
                    return await prompt.delete()
                if reaction.emoji == '🔴':
                    try:
                        color = await self.prompt_color(ctx, prompt)
                    except ValueError as e:
                        return await prompt.delete()
                role = await make_role(rolename, color, say=prompt.edit)
            else:
                prompt = await ctx.send('Pick a color or type one out! Choose ✖ for default color.')
                color = await self.prompt_color(ctx, prompt)
                role = await make_role(rolename, color, say=prompt.edit)
        await self.add_role(ctx, ctx.message.author, role)
        await ctx.message.add_reaction('👍')
    
    @role.command(name='del',aliases=['delete', 'd'],)
    @is_owner()
    async def del_roles(self, ctx, *roles: TouchableRole):
        try:
            for role in roles:
                await role.delete(reason='Via {self.bot.user.name} (bot) by {ctx.message.author.name}')
        except discord.errors.Forbidden as e:
            return await ctx.send('Missing permissions!')
        await ctx.message.add_reaction('👍')
    
    @del_roles.error
    async def cannot_into_del(self, ctx, error):
        if isinstance(error, commands.errors.BadArgument):
            await ctx.send(error)
        else:
            raise error
    
    @commands.command(name='unrole')
    async def unrole(self, ctx, *, role=None):
        """Remove a custom role from oneself or, if no args given, remove any & all custom roles"""
        async def remove_role(member, req_role, reason='Via {self.bot.user.name} (bot) by {ctx.message.author.name}'):
            await member.remove_roles(req_role, reason=reason)
            await self.check_role(req_role, member)

        if role is not None:
            role = await TouchableRole().convert(ctx, role)
            await remove_role(ctx.message.author, role)
        else:
            ext_roles = [i for i in ctx.message.author.roles if i.name.startswith(ESC)]
            for ext_role in ext_roles:
                await remove_role(ctx.message.author, ext_role)
        await ctx.message.add_reaction('👍')
    
    @commands.command(name='irole')
    @is_owner()
    async def irole(self, ctx, role: TouchableRole, *members: discord.Member):
        """Admin command to batch-assign a role"""
        for member in members:
            await self.add_role(ctx, member, role)
    
    @commands.command(name='iunrole')
    @is_owner()
    async def iunrole(self, ctx, role: TouchableRole, *members: discord.Member):
        """Admin command to batch-remove a role"""
        for member in members:
            await member.remove_roles(role)
            await self.check_role(role, member)
    
    @commands.group(name='edit', aliases=['e', 'change'], invoke_without_command=True)
    @is_owner()
    async def edit(self, ctx, role: TouchableRole, ESC=ESC):
        nums = '1⃣', '2⃣'
        prompt = await ctx.send("Do you want to edit this role's name (:one:) or its color (:two:)?")
        [await prompt.add_reaction(i) for i in nums]
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in nums and rxn.message.id == ctx.message.id and usr is ctx.message.author)
        except asyncio.TimeoutError as e:
            return await prompt.delete()
        else:
            await prompt.clear_reactions()

        if reaction.emoji == nums[0]:
            await prompt.edit(content="Type this role's new name below.")
            try:
                resp = await self.bot.wait_for('message', timeout=15.0, check=lambda msg: msg.author is ctx.message.author)
            except asyncio.TimeoutError as e:
                return
            finally:
                await prompt.delete()
            try:
                await resp.delete()
            except (discord.Forbidden, discord.HTTPException) as e:
                pass

            await role.edit(name=f'{ESC}{resp.content}')
        else:
            try:
                color = await self.prompt_color(ctx, prompt)
            except ValueError as e:
                return await prompt.delete()
            await role.edit(color=color)

        await ctx.message.add_reaction('👍')
    
    @edit.command(name='color', aliases=['colour', 'c'])
    @is_owner()
    async def edit_color(self, ctx, role):
        await role.edit(colour=color)
        await ctx.message.add_reaction('👍')
    
    @edit.command(name='name', aliases=['n'])
    @is_owner()
    async def edit_name(self, ctx, role):
        await role.edit(name=new_name)
        await ctx.message.add_reaction('👍')
    
    @edit.command(name='ESC')
    @is_owner()
    async def edit_ESC(self, ctx, old: ESC_decode, new: ESC_decode):
        """Edit the escape character that prefixes custom roles"""
        for role in ctx.guild.roles:
            if role.name.startswith(old):
                await role.edit(name=f'{new}{(role.name.lstrip(old))}')
                await asyncio.sleep(0.1)

        self.edit_ESC_var(new)
        await ctx.message.add_reaction('👍')
    
    @edit.command(name='rESC')
    @is_owner()
    async def edit_rESC(self, ctx, old: lambda arg: re.compile(arg), new: ESC_decode):
        """Same as ESC, but looks using regex instead of for a single char"""
        for role in ctx.guild.roles:
            if old.match(role.name):
                await role.edit(name=f'{new}{(role.name.lstrip(old))}')
                await asyncio.sleep(0.1)

        self.edit_ESC_var(new)
        await ctx.message.add_reaction('👍')
    
    @commands.group(name='get')
    async def get(self, ctx):
        prefix = self.bot.command_prefix(self.bot, ctx.message)
        if ctx.invoked_subcommand is None:
            await ctx.send(f'`{prefix}get members` with a given role, ' +
              f'`{prefix}get roles` (alone, all, or for a given member), '+
              f'or `{prefix}get colors` (alone, all, or for a given role)')
    
    
    @get.group(name='roles', invoke_without_command=True)
    async def roles(self, ctx, *, member: discord.Member = None):
        if member is None:
            em = discord.Embed()
            em.add_field(name='Role', value='\n'.join(f'**{role.name}**' for role in ctx.guild.roles if role.name.startswith(ESC)), inline=True)
            em.add_field(name='Members', value='\n'.join(str(len(role.members)) for role in ctx.guild.roles if role.name.startswith(ESC)), inline=True)
            return await ctx.send(embed=em)
        em = discord.Embed(title=(f'**{member.nick}** ({member.name})'  if member.nick else f'{member.name}') + ':', description='- ')
        em.description += '\n- '.join(f'**{role.name}**' for role in member.roles)
        await ctx.send(embed=em)
    
    @roles.command(name='all')
    async def all_roles(self, ctx, *, member: discord.Member = None):
        if member is None:
            em = discord.Embed()
            em.add_field(name='Role', value='\n'.join(f'**{role.name}**' for role in ctx.guild.roles), inline=True)
            em.add_field(name='Members', value='\n'.join(str(len(role.members)) for role in ctx.guild.roles), inline=True)
            return await ctx.send(embed=em)
        em = discord.Embed(title=(f'**{member.nick}** ({member.name})'  if member.nick else f'{member.name}') + ':', description='- ')
        em.description += '\n- '.join(f'**{role.name}**' for role in member.roles)
        await ctx.send(embed=em)
    
    @get.command(name='members')
    async def members(self, ctx, role: TouchableRole):
        em = discord.Embed(title=f'{role.name}:', description = '- ')
        em.description += '\n- '.join(f'**{member.nick}** ({member.name})' if member.nick else f'**{member.name}**' for member in role.members)
        await ctx.send(embed=em)
    
    @get.group(name='colors', aliases=['colours'], invoke_without_command=True)
    async def get_colors(self, ctx, *roles: TouchableRole):
        if roles:
            content, files = '', []
            for role in roles:
                content += f'**{role.name}:** `{str(role.color)[1:]}`\n'
                colorimg = Image.new('RGB', (30,30), role.color.to_rgb())
                with io.BytesIO() as bIO:
                    colorimg.save(bIO, format='PNG', optimize=True)
                    files += [discord.File(bIO.getvalue(), filename=f'{str(role.color)[1:]}.png')]
            await ctx.send(files=files, content=content)
        else:
            em = discord.Embed(description='\n'.join(f'{k} `0x{v:06x}`' for k, v in self.colors.items()))
            await ctx.send(embed=em)
    
    @get_colors.command(name='all')
    async def all_colors(self, ctx):
        em = discord.Embed()
        em.add_field(name='Emoji', value='\n'.join(f'{k} `0x{v:06x}`' for k, v in self.colors.items()))
        em.add_field(name='Default', value='\n'.join(f'**{k}:** `0x{v:06x}`' for k, v in ColorConvert().default_colors.items()))
        await ctx.send(embed=em)
        
        em = discord.Embed()
        em.add_field(name='Light', value='\n'.join(f'**{k}:** `0x{v:06x}`' for k, v in ColorConvert().light_colors.items()))
        em.add_field(name='Dark', value='\n'.join(f'**{k}:** `0x{v:06x}`' for k, v in ColorConvert().default_colors_dark.items()))
        await ctx.send(embed=em)
    
    @commands.command(name='demo',aliases=['color', 'colour'],)
    async def demo(self, ctx, *, color: ColorConvert):
        colorimg = Image.new('RGB', (100, 100), color.to_rgb())
        with io.BytesIO() as bIO:
            colorimg.save(bIO, format='PNG', optimize=True)
            await ctx.send(file=discord.File(bIO.getvalue(), filename=f'{str(color)[1:]}.png'))


def setup(bot):
    bot.add_cog(RoleManagement(bot))
