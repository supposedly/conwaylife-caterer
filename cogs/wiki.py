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
    em.description = desc

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
            query = query[len(query) > 1 and query[0] == '.':] # allow searching for numbers
            rquery = re.compile(fr'\b{query}\b', re.I)
            matches = [wiki_dyk.plaintext.index(i) for i in wiki_dyk.plaintext if rquery.search(i)]
            if not matches:
                return await ctx.send(f'No results found for `{query}`.')
            em.description = ''
            for item in matches[:3]:
                em.description += f'**#{item}:** {wiki_dyk.trivia[item]}\n'
            em.set_footer(text=f'Showing first three or fewer DYK results for "{query}"')
            await ctx.send(embed=em)
        else:
            raise error

    @commands.group(name='wiki', aliases=cmd.aliases['wiki'], invoke_without_subcommand=True)
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
            em.set_thumbnail(url='https://i.imgur.com/pZmruZg.png')
            return await ctx.send(embed=em)
        
        if not query: # get pattern of the week instead
            async with aiohttp.ClientSession() as rqst:
                async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=Main_Page') as resp:
                    data = await resp.text()
            
            pgtxt = json.loads(data)["parse"]["text"]["*"]
            data = data.split('Download.')[0]
            try:
                pgimg = (rpgimg.search(data) or rpgimgfallback.search(data) or rthumb.search(data)).group()
            except AttributeError as e:
                print(e)
                pass
            else:
                print(pgimg)
                em.set_thumbnail(url=f'http://conwaylife.com{pgimg}')
            info = rpotw.search(pgtxt)
            
            em.title="This week's featured article"
            em.url = f'http://conwaylife.com{info.group(1)}' # pgtitle=info.group(2)
            em.description = parse(pgtxt.split('a></div>')[1].split('<div align')[0], potw=True)
            
            return await ctx.send(embed=em)
        
        async with aiohttp.ClientSession() as rqst:
            async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}') as resp:
                pgtxt = await resp.text()
                
            if '>REDIRECT ' in pgtxt:
                em.set_footer(text='(redirected from "' + query + '")')
                query = rredirect.search(pgtxt).group(1)
                async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}') as resp:
                    pgtxt = await resp.text()
            if 'missingtitle' in pgtxt or 'invalidtitle' in pgtxt:
                await ctx.send('Page `' + query + '` does not exist.') # no sanitization yeet
            else:
                data = json.loads(pgtxt)
                if '(disambiguation)' in data["parse"]["title"]:
                    edit = True
                    emb = disambig(data)
                    links = emb[1]
                    emb = emb[0]
                    msg = await ctx.send(embed=emb)
                    
                    def check(rxn, user): # too long for lambda :(
                        return user == ctx.message.author and rxn.emoji in numbers_fu[:len(links)] and rxn.message.id == msg.id
                        
                    for i in range(len(links)):
                        try:
                            await msg.add_reaction(numbers_fu[i])
                        except IndexError as e:
                            await msg.clear_reactions()
                            return await msg.add_reaction(self.bot.get_emoji(371495166277582849))
                        
                    try:
                        react, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                    except asyncio.TimeoutError as e:
                        return await msg.clear_reactions()
                    
                    query = links[numbers_fu.index(react.emoji)]
                    async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}') as resp:
                        pgtxt = await resp.text()
                        data = json.loads(pgtxt)
                
                pgtxt = pgtxt.split('Category:' if 'Category:' in pgtxt else '/table')[0]
                pgimg = rpgimg.search(pgtxt) or rpgimgfallback.search(pgtxt) or rthumb.search(pgtxt)
                pgimg = pgimg.group() if pgimg else None
                
                await regpage(data, query, rqst, em, pgimg)
                
                if edit:
                    await msg.edit(embed=em)
                    await msg.clear_reactions()
                else:
                    await ctx.send(embed=em)
    
    @wiki.group(name='rle', aliases=['r', 'RLE'], invoke_without_subcommand = True)
    async def rle(self, ctx, *, query):
        pass
    
    @rle.command(name='synth', aliases=['s', 'synthesis'])
    async def synth(self, ctx, *, query):
        pass        

def setup(bot):
    bot.add_cog(Wiki(bot))
