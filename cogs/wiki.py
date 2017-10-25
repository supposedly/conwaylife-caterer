import discord
from discord.ext import commands
import asyncio, aiohttp
import re
import json
from html import unescape
from collections import namedtuple
from cogs.resources import wiki_dyk
from random import randint

rparens = re.compile(r" \(.+?\)")
rbracks = re.compile(r"\[.+?\]")
rtags = re.compile(r"<.+?>", re.S)
rredherring = re.compile(r"<p>.{0,10}</p>", re.S) #to prevent `<p><br />\n</p>` as in the Simkin Glider Gun page, stupid hack
rctrlchars = re.compile(r"\\.") #needs to be changed maybe
rredirect = re.compile(r'">(.+?)</a>')

rgif = re.compile(r"File[^F]+?\.gif")
rimage = re.compile(r"File[^F]+?\.png")

rlinks = re.compile(r'<li> ?<a href="(.+?)".+?>(.+?)</a>')
rlinksb = re.compile(r'<a href="(.+?)".*?>(.*?)</a>')
rdisamb = re.compile(r'<li> ?<a href="/wiki/(.+?)"')

rnewlines = re.compile(r"\n+")

numbers_fu = [u'\u0031\u20E3', u'\u0032\u20E3', u'\u0033\u20E3', u'\u0034\u20E3', u'\u0035\u20E3', u'\u0036\u20E3', u'\u0037\u20E3', u'\u0038\u20E3', u'\u0039\u20E3']

def parse(txt):
    txt = rredherring.sub('', txt)
    txt = txt.replace('<b>', '**').replace('</b>', '**').split('<p>', 1)[1].split('</p>')[0]
    txt = rctrlchars.sub('', txt)
    txt = rparens.sub('', txt)
    txt = rbracks.sub('', txt)
    txt = rlinksb.sub(lambda m: f'[{m.group(2)}](http://conwaylife.com{m.group(1)})', txt)
    txt = rtags.sub('', txt)
    return txt

async def regpage(data, query, rqst, em):
    images = await rqst.get(f'http://conwaylife.com/w/api.php?action=query&prop=images&format=json&titles={query}')
    images = images.text()
    pgimg = rgif.search(images)
    find = rimage.findall(images)
    pgimg = (pgimg.group(0) if pgimg else (min(find, key = len) if find else ''))
    images = await rqst.json(f'http://conwaylife.com/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles={pgimg}')
    try:
        pgimg = list(images["query"]["pages"].values())[0]["imageinfo"][0]["url"]
        em.set_thumbnail(url=pgimg)
    except (KeyError, TypeError):
        pass

    pgtitle = data["parse"]["title"]
    desc = unescape(parse(data["parse"]["text"]["*"]))

    em.title = f'{pgtitle}'
    em.url = f'http://conwaylife.com/wiki/{pgtitle.replace(" ", "_")}'
    em.description = desc

def parsedisambig(txt):
    txt = txt.replace('<b>', '').replace('</b>', '')
    # think ^ should stay this way so the title doesn't clash visually with the options, but ('' --> '**') if you ever wanna change it in the future
    links = rdisamb.findall(txt)
    txt = rlinks.sub(lambda m: f'**{m.group(2)}**', txt) # change to '**[{m.group(2)}](http://conwaylife.com{m.group(1)})**' for hyperlink although it looks really ugly
    txt = rlinksb.sub(lambda m: f'[{m.group(2)}](http://conwaylife.com{m.group(1)})', txt)
    
    txt = rtags.sub('', txt)
    
    txt = rnewlines.sub('\n', txt)
    return (txt, links)

def disambig(data):
    pgtitle = data["parse"]["title"]
    desc_links = parsedisambig(data["parse"]["text"]["*"])
    return (discord.Embed(title=f'**{pgtitle}**', url=f'http://conwaylife.com/wiki/{pgtitle.replace(" ", "_")}', description=desc_links[0], color=0xffffff), desc_links[1])

class Wiki:
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='dyk', aliases=['DYK'])
    async def dyk(self, ctx, *num: int):
        if not num:
            num = (randint(0, 91),)
        em = discord.Embed()
        em.color = 0xffffff
        em.title = 'Did you know...'
        em.description = ''
        for item in num:
            em.description += f'**#{item}:** {wiki_dyk.trivia[item - 1]}\n'
        await ctx.send(embed=em)
        

    @commands.command(name='wiki')
    async def wiki(self, ctx, *, query: str):
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
            em.title = '**Methusynthesae**'
            em.description = gus
            em.url = 'http://conwaylife.com/forums/viewtopic.php?f=2&t=1600'
            em.set_thumbnail(url='https://i.imgur.com/CQefDXF.png')
            await ctx.send(embed=em)
        else:
            async with aiohttp.ClientSession() as rqst:
                async with rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}') as data:
                    data = await data.text()
                    if '>REDIRECT ' in data:
                        em.set_footer(text='(redirected from "' + query + '")')
                        query = rredirect.search(data).group(1)
                        data = rqst.get(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}').text
                        
                    if 'missingtitle' in data:
                        await ctx.send('Page `' + query + '` does not exist.') # no sanitization yeet
                    if 'invalidtitle' in data:
                        await ctx.send(f'Invalid title: `{query}`')
                    else:
                        data = json.loads(data)
                        if '(disambiguation)' in data["parse"]["title"]:
                            edit = True
                            emb = disambig(data)
                            links = emb[1]
                            emb = emb[0]
                            msg = await ctx.send(embed=emb)
                            for i in range(len(links)):
                                await msg.add_reaction(numbers_fu[i])
                            try:
                                react, user = await self.bot.wait_for('reaction_add', timeout=30.0, check = lambda react, user: user == ctx.message.author and react.emoji in numbers_fu[:len(links)])
                            except asyncio.TimeoutError:
                                await msg.clear_reactions()
                                return
                            query = links[numbers_fu.index(react.emoji)]
                            data = await rqst.json(f'http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page={query}')
                        
                        await regpage(data, query, rqst, em)
                        if edit:
                            await msg.edit(embed=em)
                            await msg.clear_reactions()
                        else:
                            await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(Wiki(bot))
