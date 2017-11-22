import discord
from discord.ext import commands
from PIL import Image
import concurrent.futures
import os, asyncio, io

@commands.check
async def block_outside_lounge(ctx):
    return ctx.guild.id == 357922255553953794

class ColorConvert(commands.ColourConverter): # equivalent to commands.ColorConverter except 
    def __init__(self):
        super().__init__()
        self.colors = {'✖': 0, '❤': 0xbe1931, '💛': 0xfdcb58, '💚': 0x78b159, '💙': 0x5dadec, '💜': 0xaa8ed6, '⚪': 0xffffff, '⚫': 0x010101}
    
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except commands.errors.BadArgument as e:
            try:
                return discord.Colour(self.colors[argument])
            except ValueError as e:
                return self.colors

class LowRole(commands.RoleConverter):
    async def convert(self, ctx, argument):
        return await super().convert(ctx, argument.lower())

def is_owner():
    async def predicate(ctx):
        return ctx.author is ctx.guild.owner
    return commands.check(predicate)

class RoleManager:
    def __init__(self, bot):
        self.bot = bot
        self.colors = {'✖': 0, '❤': 0xbe1931, '💛': 0xfdcb58, '💚': 0x78b159, '💙': 0x5dadec, '💜': 0xaa8ed6, '⚪': 0xffffff, '⚫': 0x010101}
    
    @commands.group(name='role', invoke_without_command=True)
    async def role(self, ctx, role: LowRole, *members: discord.Member):
        async def add_role_to(member, reason=f'Via {self.bot.user.name} by {ctx.message.author.name}'):
            return await member.add_roles(role, reason=reason)
        
        custom_roles = [i for i in ctx.guild.roles if not i.name[0].isupper()]
        
        if not ctx.message.author is ctx.guild.owner or not members:
            await add_role_to(ctx.message.author)
            return await ctx.message.add_reaction('👍')
        for member in members:
            has_roles = [i in custom_roles for i in member.roles]
            if any(has_roles):
                for dupl_role in [member.roles[k] for k in [i for i, j in enumerate(has_roles) if j]]:
                    await ctx.invoke(self.unrole, dupl_role, member)
            try:
                await add_role_to(member)
            except discord.errors.Forbidden as e:
                return await ctx.send('You have to give me the "Manage Roles" permission!')
        await ctx.message.add_reaction('👍')

    @role.error
    async def create_role_or_raise(self, ctx, error):
        if isinstance(error, commands.errors.BadArgument):
            say = ctx.send
            reaction, created, is_color = False, True, True
            req_role, *members = ctx.message.content.split()[1:]
            all_roles = {i.color: i.name for i in ctx.guild.roles}
            if members:
                try:
                    await commands.MemberConverter().convert(ctx, members[0])
                except Exception as e:
                    try:
                        resp = await ColorConvert().convert(ctx, req_role)
                    except KeyError as e:
                        try:
                            resp = await ColorConvert().convert(ctx, f'{req_role}_{members[0]}')
                        except (KeyError, IndexError) as e:
                            req_role, members = '{} {}'.format(req_role, ' '.join(members)), None
                            is_color = False
                        else:
                            req_role += f' {members.pop(0)}'
                    
                    if is_color:
                        req_role, members = ' '.join(members), None
                        if resp in all_roles:
                            req_role = all_roles[resp]
                            created = None
                        if req_role not in all_roles.values():
                            all_roles[resp.value] = req_role
                        else:
                            resp = list(all_roles.keys())[list(all_roles.values()).index(req_role)]
                            created = False if created else None
                    
            elif req_role in all_roles.values():
                return await ctx.send(f'No members given to assign role `{req_role}`!')
            
            if req_role not in all_roles.values():
                try:
                    resp = await ColorConvert().convert(ctx, req_role)
                except KeyError as e:
                    try:
                        resp = await ColorConvert().convert(ctx, f'{req_role}_{members[0]}')
                    except (KeyError, IndexError) as e:
                        resp = None
                    else:
                        req_role += f' {members.pop(0)}'
                if resp and resp.value in all_roles:
                    req_role = all_roles[resp.value]
                elif not resp:
                    prompt = await ctx.send(f'Create role `{req_role}`' + (f' with color `{resp}`?\n(Red dot to create this role with custom color)' if resp else '?'))
                    
                    say = prompt.edit
                    
                    rxns = ('✅',) + (('🔴', '❌') if resp else ('❌',))
                    [await prompt.add_reaction(i) for i in rxns]
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in rxns and rxn.message.id == prompt.id and usr is ctx.message.author)
                    except asyncio.TimeoutError as e:
                        return await prompt.delete()
                    else:
                        await prompt.clear_reactions()
                    if reaction.emoji == '❌':
                        return await prompt.delete()
                    
                if (not resp) or (resp and reaction and reaction.emoji == '🔴'):
                    await prompt.edit(content="Pick a color or type one out! Choose ✖ for default.")
                    [await prompt.add_reaction(color_emote) for color_emote in self.colors]
                    futures = [
                    self.bot.wait_for('message', timeout=15.0, check=lambda msg: msg.author == ctx.message.author),
                    self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in self.colors and rxn.message.id == prompt.id and usr is ctx.message.author)
                    ]
                    resp = await asyncio.wait(futures, loop=self.bot.loop, timeout=15.0, return_when=concurrent.futures.FIRST_COMPLETED) # returns two sets, Finished and Pending
                    try:
                        [resp] = resp[0] # unpack sole value of Finished set (will only have one value bc only one of the two coros can finish first)
                    except ValueError as e: # if neither task completed then there will be nothing in the Finished set
                        return await prompt.delete()
                    else:
                        await prompt.clear_reactions()
                        resp = resp.result()
                        resp = await ColorConvert().convert(ctx, resp.content if isinstance(resp, discord.Message) else resp[0].emoji)
            
            req_role = req_role.lower()
            req_role = await ctx.guild.create_role(name=req_role, color=resp, reason=f'Via {self.bot.user.name} by {ctx.message.author.name}')
            
            if created is None:
                await say(content=f'Successfully assigned extant role (`{req_role.name}`) for color `{resp}`!')
            elif created:
                await say(content=f'Successfully created role `{req_role.name}` with color `{resp}`! Its permissions can now be edited manually.')

            if members:
                await ctx.invoke(self.role, req_role, *[await commands.MemberConverter().convert(ctx, i) for i in members])
            else:
                await ctx.invoke(self.role, req_role, ctx.message.author)

    @role.command(name='del', aliases=['delete', 'd'])
    @is_owner()
    async def del_roles(self, ctx, *, role: LowRole):
        try:
            await role.delete(reason=f'Via {self.bot.user.name} by {ctx.message.author.name}')
        except discord.errors.Forbidden as e:
            return await ctx.send('You need to give me the "Manage Roles" permission!')
        await ctx.message.add_reaction('👍')

    @del_roles.error
    async def cannot_into_del(self, ctx, error):
        if isinstance(error, commands.errors.BadArgument):
            await ctx.send(error)
        else:
            raise error

    @commands.group(name='edit', aliases=['e', 'change'], invoke_without_command=True)
    @is_owner()
    async def edit(self, ctx, role: LowRole):
        nums = ['1\u20E3', '2\u20E3']
        prompt = await ctx.send("Do you want to edit this role's name (:one:) or its color (:two:)?")
        [await prompt.add_reaction(i) for i in nums]
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in nums and rxn.message.id == prompt.id and usr is ctx.message.author)
        except asyncio.TimeoutError as e:
            return await prompt.delete()
        else:
            await prompt.clear_reactions()
        
        if reaction.emoji == nums[0]:
            await prompt.edit(content="Type this role's new name below.")
            try:
                resp = await self.bot.wait_for('message', timeout=15.0, check=lambda msg: msg.author == ctx.message.author)
            except asyncio.TimeoutError as e:
                return
            finally:
                await prompt.clear_reactions()
                await prompt.delete()
                try:
                    await resp.delete()
                except (discord.Forbidden, discord.HTTPException) as e:
                    pass
            await role.edit(name=resp.content)
        else:
            await prompt.edit(content='Pick a color! Choose ✖ for default color.')
            [await prompt.add_reaction(color_emote) for color_emote in self.colors]
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=lambda rxn, usr: rxn.emoji in self.colors and rxn.message.id == prompt.id and usr is ctx.message.author)
            except asyncio.TimeoutError as e:
                return
            else:
                await prompt.clear_reactions()
            finally:
                await prompt.delete()
            await role.edit(color=discord.Colour(self.colors[reaction.emoji]))
        await ctx.message.add_reaction('👍')

    @edit.command(name='color', aliases=['colour', 'c'])
    @is_owner()
    async def edit_color(self, ctx, role: LowRole, *, color: ColorConvert=0):
        await role.edit(colour=color)
        await ctx.message.add_reaction('👍')

    @edit.command(name='name', aliases=['n'])
    @is_owner()
    async def edit_name(self, ctx, role: LowRole, *, new_name):
        await role.edit(name=new_name)
        await ctx.message.add_reaction('👍')

    @commands.command(name='unrole')
    async def unrole(self, ctx, role: LowRole, *members: discord.Member):
        
        async def remove_role_from(member, reason=f'Via {self.bot.user.name} by {ctx.message.author.name}'):
            await member.remove_roles(role, reason=reason)
            if len(role.members) <= 1:
                await role.delete(reason=f'Via {self.bot.user.name} by {ctx.message.author.name}')
        
        if ctx.message.author is not ctx.guild.owner or not members:
            await remove_role_from(ctx.message.author)
        else:
            for member in members:
                try:
                    await remove_role_from(member)
                except discord.errors.Forbidden as e:
                    return await ctx.send('You need to give me the "Manage Roles" permission!')
                except discord.errors.NotFound as e:
                    pass
        await ctx.message.add_reaction('👍')
    
    @unrole.error
    async def multi_word_rolename(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            rolename = ' '.join(ctx.message.content.split()[1:])
            return await ctx.invoke(self.unrole, await LowRole().convert(ctx, rolename))

    @commands.group(name='get')
    async def get(self, ctx):
        prefix = self.bot.command_prefix(self.bot, ctx.message)
        if ctx.invoked_subcommand is None:
            await ctx.send(f'`{prefix}get members` with a given role, or `{prefix}get roles` for a given member')

    @get.command(name='roles')
    async def roles(self, ctx, member: discord.Member=None):
        if member is None:
            em = discord.Embed()
            em.add_field(name='Roles', value='\n'.join(f'**{role.name}**' for role in ctx.guild.roles), inline=True)
            em.add_field(name='Members', value='\n'.join(str(len(role.members)) for role in ctx.guild.roles), inline=True)
            return await ctx.send(embed=em)
        em = discord.Embed(title=(f'**{member.nick}** ({member.name})'  if member.nick else f'{member.name}') + ':', description='- ')
        em.description += '\n- '.join(f'**{role.name}**' for role in member.roles)
        await ctx.send(embed=em)

    @get.command(name='members')
    async def members(self, ctx, role: LowRole):
        em = discord.Embed(title=f'{role.name}:', description = '- ')
        em.description += '\n- '.join(f'**{member.nick}** ({member.name})' if member.nick else f'**{member.name}**' for member in role.members)
        await ctx.send(embed=em)

    @get.command(name='colors', aliases=['colours'])
    async def get_colors(self, ctx, *roles: LowRole):
        if roles:
            content, files = '', []
            for role in roles:
                content += f'{role.name}: `{role.color.value}`\n'
                colorimg = Image.new('RGB', (30,30), role.color.to_rgb())
                with io.BytesIO() as bIO:
                    colorimg.save(bIO, format='PNG', optimize=True)
                    files += [discord.File(bIO.getvalue(), filename=f'{role.color.value}.png')]
            await ctx.send(files=files, content=content)
        else:
            em = discord.Embed(description='\n'.join(f'{k} `0x{v:06x}`' for k, v in self.colors.items()))
            await ctx.send(embed=em)

    @commands.command(name='demo', aliases=['color', 'colour'])
    async def demo(self, ctx, *, color: ColorConvert):
        colorimg = Image.new('RGB', (100,100), color.to_rgb())
        with io.BytesIO() as bIO:
            colorimg.save(bIO, format='PNG', optimize=True)
            await ctx.send(file=discord.File(bIO.getvalue(), filename='demo.png'))

def setup(bot):
    bot.add_cog(RoleManager(bot))
