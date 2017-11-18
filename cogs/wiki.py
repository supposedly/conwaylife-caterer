import discord, aiohttp, asyncio
import re, json, html
from discord.ext import commands
from cogs.resources import wiki_dyk, cmd
from collections import namedtuple
from random import randint

rparens = re.compile(r' \(.+?\)')
rbracks = re.compile(r'\[.+?\]')
rtags = re.compile(r'<.+?>', re.S)
rredherring = re.compile(r'<p>.{0,10}</p>', re.S) # to prevent `<p><br />\n</p>` as in the Simkin Glider Gun page, stupid hack
rctrlchars = re.compile(r'\\.') # needs to be changed maybe
rredirect = re.compile(r'">(.+?)</a>')
rgif = re.compile(r'File[^F]+?\.gif')
rimage = re.compile(r'File[^F]+?\.png')
rlinks = re.compile(r'<li> ?<a href="(.+?)".+?>(.+?)</a>')
rlinksb = re.compile(r'<a href="(.+?)".*?>(.*?)</a>')
rdisamb = re.compile(r'<li> ?<a href="/wiki/(.+?)"')
rnewlines = re.compile(r"\n+")
rpgimg = re.compile(r'(?<=f=\\")/w/images/[a-z\d]+?/[a-z\d]+?/[\w]+\.(?:png|gif)') # matches <a href="/w/images/0/03/Rats.gif" but not src="/w/images/0/03/Rats.gif"
rpgimgfallback = re.compile(r'(?<=c=\\")/w/images/[a-z\d]+?/[a-z\d]+?/[\w]+\.(?:png|gif)') # matches src= in case of no href=
rthumb = re.compile(r'(?<=c=\\")/w/images/thumb/[a-z\d]+?/[a-z\d]+?/([\w]+\.(?:png|jpg|gif))/\d+px-\1') # matches thumbnail URL format
rpotw = re.compile(r'><a href="(.+?)" title="(.+?)">Read more...') #feel like the starting > shouldn't be there but it won't work without

numbers_fu = [u'\u0031\u20E3', u'\u0032\u20E3', u'\u0033\u20E3', u'\u0034\u20E3', u'\u0035\u20E3', u'\u0036\u20E3', u'\u0037\u20E3', u'\u0038\u20E3', u'\u0039\u20E3']

def parse(txt, potw=False):
    if not potw:
        txt = rredherring.sub('', txt)
        txt = txt.split('<p>', 1)[1].split('</p>')[0]
    txt = txt.replace('<b>', '**').replace('</b>', '**')
    txt = rctrlchars.sub('', txt) # likely does nothing
    txt = rparens.sub('', txt)
    txt = rbracks.sub('', txt)
    txt = rlinksb.sub(lambda m: f'[{m.group(2)}](http://conwaylife.com{m.group(1)})', txt)
    txt = rtags.sub('', txt)
    return html.unescape(txt)

async def regpage(data, query, rqst, em, pgimg):
    if pgimg:
        pgimg = f'http://conwaylife.com{pgimg}'
    else:
        async with rqst.get(f'http://conwaylife.com/w/api.php?action=query&prop=images&format=json&titles={query}') as resp:
            images = await resp.text()
        pgimg = rgif.search(images)
        find = rimage.findall(images)
        pgimg = pgimg.group() if pgimg else (min(find, key=len) if find else '')
        async with rqst.get(f'http://conwaylife.com/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles={pgimg}') as resp:
            images = await resp.json()
        try:
            pgimg = list(images["query"]["pages"].values())[0]["imageinfo"][0]["url"]
        except (KeyError, TypeError) as e:
            pass
    em.set_thumbnail(url=pgimg)

    pgtitle = data["parse"]["title"]
    desc = parse(data["parse"]["text"]["*"])

    em.title = f'{pgtitle}'
    em.url = f'http://conwaylife.com/wiki/{pgtitle.replace(" ", "_")}'
    em.description = desc.replace('Cite error: <ref> tags exist, but no <references/> tag was found', '')

def disambig(data):
    def parse_disamb(txt):
        txt = txt.replace('<b>', '').replace('</b>', '')
        links = rdisamb.findall(txt)
        txt = rlinks.sub(lambda m: f'**{m.group(2)}**', txt) # change to '**[{m.group(2)}](http://conwaylife.com{m.group(1)})**' for hyperlink although it looks really ugly
        txt = rlinksb.sub(lambda m: f'[{m.group(2)}](http://conwaylife.com{m.group(1)})', txt)
        txt = rtags.sub('', txt)
        txt = rnewlines.sub('\n', txt)
        return txt, links
    pgtitle = data["parse"]["title"]
    desc_links = parse_disamb(data["parse"]["text"]["*"])
    emb = discord.Embed(title=f'{pgtitle}', url=f'http://conwaylife.com/wiki/{pgtitle.replace(" ", "_")}', description=desc_links[0], color=0xffffff)
    return emb, desc_links[1]

class Wiki:
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='dyk', aliases=cmd.aliases['dyk'])
    async def dyk(self, ctx, *num: int):
        if num == ():
            num = randint(0, 91),
        indices = ((91 if not i else (i - 1) % 92) for i in num)
        em = discord.Embed()
        em.color = 0xffffff
        em.title = 'Did you know...\n'
        em.description = ''
        for item in indices:
            em.description += f'**#{item + 1}:** {wiki_dyk.trivia[item]}\n'
        await ctx.send(embed=em)
    
    @dyk.error
    async def dyk_search(self, ctx, error):
        # is it bad practice to abuse the error handler like this? ...probably
        if isinstance(error, commands.BadArgument):
            em = discord.Embed()
            em.color = 0xffffff
            em.title = 'Did you know...\n'
            
            # remove invocation from message and keep query, since we can't do ctx.args here
            query = ctx.message.content.split(' ', 1)[1].rstrip()
            query = query[len(query) > 1 and query[0] == '.' and query[1:].isdigit():] # allow searching for numbers by prepending a period
            rquery = re.compile(fr'\b{re.escape(query)}\b', re.I)
            matches = [wiki_dyk.plaintext.index(i) for i in wiki_dyk.plaintext if rquery.search(i)]
            if not matches:
                return await ctx.send(f'No results found for `{query}`.')
            em.description = ''
            for item in matches[:3]:
                em.description += f'**#{item + 1}:** {wiki_dyk.trivia[item]}\n'
            em.set_footer(text=f'Showing first three or fewer DYK results for "{query}"')
            await ctx.send(embed=em)
        else:
            raise error
    
    async def handle_page(self, ctx, rqst, query, num=0):
        print(ctx, rqst)
        say = ctx.send
        async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section={num}&page={query}') as resp:
            pgtxt = await resp.text()
            
        if '>REDIRECT ' in pgtxt:
            query = rredirect.search(pgtxt).group(1)
            async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section={num}&page={query}') as resp:
                pgtxt = await resp.text()
        elif 'missingtitle' in pgtxt or 'invalidtitle' in pgtxt:
            await ctx.send('Page `' + query + '` does not exist.') # no sanitization yeet
            raise ValueError
        
        data = json.loads(pgtxt)
        if '(disambiguation)' in data["parse"]["title"]:
            emb = disambig(data)
            links, emb = emb[1], emb[0]
            msg = await ctx.send(embed=emb)
            say = msg.edit
            
            def check(rxn, user): # too long for lambda :(
                return user == ctx.message.author and rxn.emoji in numbers_fu[:len(links)] and rxn.message.id == msg.id
                
            for i in range(len(links)):
                try:
                    await msg.add_reaction(numbers_fu[i])
                except IndexError as e:
                    await msg.clear_reactions()
                    await msg.add_reaction(self.bot.get_emoji(371495166277582849))
                    raise e
            try:
                react, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError as e:
                raise e
            finally:
                await msg.clear_reactions()
            query = links[numbers_fu.index(react.emoji)]
            async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section={num}&page={query}') as resp:
                pgtxt = await resp.text()
        return pgtxt, data, say
    
    @commands.group(name='wiki', aliases=cmd.aliases['wiki'], invoke_without_command=True)
    async def wiki(self, ctx, *, query=''):
        if query[:1].lower() + query[1:] == 'caterer':
            await ctx.message.add_reaction('👋')
        await ctx.channel.trigger_typing()
        em = discord.Embed()
        em.color = 0x000000
        
        edit = False
        
        if query[:1].lower() + query[1:] == 'methusynthesis':
            em.set_footer(text=f'(redirected from "{query}")')
            query = 'methusynthesae'
        if query[:1].lower() + query[1:] == 'methusynthesae':
            gus = "**Methusynthesae** are patterns/methuselah that basically/mildly are spaceship reactions, though it is a bit hard to explain the relation. It is way different from syntheses because they *are* patterns, and **don't** form other patterns."
            em.title = 'Methusynthesae'
            em.description = gus
            em.url = 'http://conwaylife.com/forums/viewtopic.php?f=2&t=1600'
            em.set_thumbnail(url='attachment://methusynthesis1.png')
            return await ctx.send(file=discord.File('./cogs/resources/methusynthesis1.png', 'methusynthesis1.png'), embed=em)
        
        if not query: # get pattern of the week instead
            async with aiohttp.ClientSession() as rqst:
                async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=Main_Page') as resp:
                    data = await resp.text()
            
            pgtxt = json.loads(data)["parse"]["text"]["*"]
            data = data.split('Download.')[0]
            try:
                pgimg = (rpgimg.search(data) or rpgimgfallback.search(data) or rthumb.search(data)).group()
            except AttributeError as e:
                pass
            else:
                em.set_thumbnail(url=f'http://conwaylife.com{pgimg}')
            info = rpotw.search(pgtxt)
            
            em.title="This week's featured article"
            em.url = f'http://conwaylife.com{info.group(1)}' # pgtitle=info.group(2)
            em.description = parse(pgtxt.split('a></div>')[1].split('<div align')[0], potw=True)
            
            return await ctx.send(embed=em)
        
        async with aiohttp.ClientSession() as rqst:
            try:
                pgtxt, data, say = await self.handle_page(ctx, rqst, query)
            except (ValueError, IndexError, asyncio.TimeoutError) as e:
                return
            
            pgtxt = pgtxt.split('Category:' if 'Category:' in pgtxt else '/table')[0]
            pgimg = rpgimg.search(pgtxt) or rpgimgfallback.search(pgtxt) or rthumb.search(pgtxt)
            pgimg = pgimg.group() if pgimg else None
            
            await regpage(data, query, rqst, em, pgimg)
            
            await say(embed=em)
            if edit:
                await msg.clear_reactions()
   
    def normalized_filetype(filetype):
        filerefs = {('5', '105', 'l105', 'lif105'): '_105.lif', ('6', '106', 'l106', 'lif106'): '_106.lif', ('r', 'rle', 'RLE'): '.rle', ('t', 'plaintext', 'text', 'cells'): '.cells'}
        normalized = filetype.strip('.').lower()
        return [filerefs[v] for v in filerefs if normalized in v][0] if any(normalized in v for v in filerefs) else (filetype,)
    
    @staticmethod
    def normalized_query(query):
        return query[0].upper() + query[1:]
    
    async def send_info(self, ctx, rqst, pgtxt, query, caller, say, filetype):
        search = {'pat': (' Pattern files', 'pattern file', 'Pattern files'), 'synth': ('>Glider synthesis<', 'glider synthesis')}
        if search[caller][0] in pgtxt:
            rpat = re.compile(fr'http://www\.conwaylife\.com/patterns/[\w\-. ]+?{filetype}', re.I)
            patfile = rpat.search(pgtxt.split('Pattern files', 1)[-1+(caller=='synth')])
            
            if patfile:
                async with rqst.get(patfile.group()) as resp:
                    msgtext = '```makefile\n{}```'.format(await resp.text())
                try:
                    await say(content=msgtext, embed=None)
                except discord.errors.HTTPException as e:
                    await say(content=f'Page `{query}` either has no {search[caller][1]} or its file is too large to send via Discord.', embed=None)
            else:
                await say(content=f'Page `{query}` contains no {search[caller][1]}.', embed=None)
        else:
            await say(content=f'Page `{query}` lists no {search[caller][1]}.', embed=None)
    
    @wiki.command(name='-pat', aliases=['-p', '-pattern'])
    async def pat(self, ctx, filetype: normalized_filetype, *, query=''):
        async with ctx.typing():
            if isinstance(filetype, tuple):
                query = f'{filetype[0]} {query}'
                filetype = '.rle'
            
            async with aiohttp.ClientSession() as rqst:
                try:
                    pgtxt, data, say = await self.handle_page(ctx, rqst, query)
                except (ValueError, IndexError, asyncio.TimeoutError) as e:
                    return
                
                query = self.normalized_query(query)
                await self.send_info(ctx, rqst, pgtxt, query, 'pat', say, re.escape(filetype))
    
    
    @wiki.command(name='-synth', aliases=['-s', '-synthesis'])
    async def synth(self, ctx, *, query):
        async with aiohttp.ClientSession() as rqst:
            async with ctx.typing():
                try:
                    pgtxt, data, say = await self.handle_page(ctx, rqst, query)
                except (ValueError, IndexError, asyncio.TimeoutError) as e:
                    return
                
            query = self.normalized_query(query)
            await self.send_info(ctx, rqst, pgtxt, query, 'synth', say, filetype=r'\.\w+')  

def setup(bot):
    bot.add_cog(Wiki(bot))
