import asyncio
import json
import html
import random
import re

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import commands

from cogs.resources import cmd, wiki_dyk, mutils

rDIRTY = re.compile(r' ?[([].+?[\])]|\\.')
rTAGS = re.compile('<.+?>', re.S)
rREDHERRING = re.compile(r'<p>.{0,10}</p>', re.S) # to prevent `<p><br />\n</p>` as in the Simkin Glider Gun page, stupid hack
rREDIRECT = re.compile(r'">(.+?)</a>')
rLINKS = re.compile(r'<a href="(.+?)".*?>(.*?)</a>')
rPGIMG = re.compile(r'(?<=f=\\"|ef=")/w/images/[a-z\d]+?/[a-z\d]+?/[\w]+\.(?:png|gif)') # matches <a href="/w/images/0/03/Rats.gif" but not src="/w/images/0/03/Rats.gif"
rPGIMGFALLBACK = re.compile(r'(?<=c=\\"|rc=")/w/images/[a-z\d]+?/[a-z\d]+?/[\w]+\.(?:png|gif)') # matches src= in case of no href=
rTHUMB = re.compile(r'(?<=c=\\"|rc=")/w/images/thumb/[a-z\d]+?/[a-z\d]+?/([\w]+\.(?:png|jpg|gif))/\d+px-\1') # matches thumbnail URL format
rPOTW = re.compile(r'><a href="(/wiki/(?!File:).+?)" title="(.+?)">Read more\.\.\.') # matches the URL and title of the 'Read more...' link


class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=bot.loop)
    
    def clean(self, txt, potw=False, *, WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        txt = txt if potw else rDIRTY.sub(
          '',
          str(next((p for p in BeautifulSoup(txt, 'lxml').find_all("p") if len(p.text) > 10), txt))
          .replace("<b>", "**")
          .replace("</b>", "**")
          )
        return html.unescape(rTAGS.sub('', rLINKS.sub(rf'[\g<2>]({WIKI_URL}\g<1>)', txt)))
    
    async def page_img(self, query, img_name=None, *, WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        if img_name is None:
            async with self.session.get(f'{WIKI_URL}{API_SUF}?action=query&prop=images&format=json&titles={query}') as resp:
                images = await resp.json()
            pglist = images["query"]["pages"].values()
            for page in pglist: # uh
                try:
                    img_name = page["images"][0]
                except KeyError as e:
                    continue
                if 'missing' not in img_name:
                    img_name = img_name["title"]
                    break
            else:
                raise IndexError
        async with self.session.get(f'{WIKI_URL}{API_SUF}?action=query&prop=imageinfo&iiprop=url&format=json&titles={img_name}') as resp:
            img_dir = (await resp.json())["query"]["pages"].values()
        try:
            pgimg = list(img_dir)[0]["imageinfo"][0]["url"]
        except (KeyError, TypeError) as e:
            raise
        else:
            return pgimg
    
    async def regpage(self, data, query, em, pgimg, suffix='', *, WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        pgtitle = data["parse"]["title"]
        desc = self.clean(data["parse"]["text"]["*"], WIKI_URL=WIKI_URL, API_SUF=API_SUF)
        em.title = f'{pgtitle}{suffix}'
        em.url = f'{WIKI_URL}/wiki/{pgtitle.replace(" ", "_")}'
        em.description = desc.replace('Cite error: <ref> tags exist, but no <references/> tag was found', '')
        try:
            em.set_thumbnail(url=f'{WIKI_URL}{pgimg}' if pgimg else await self.page_img(query, WIKI_URL=WIKI_URL, API_SUF=API_SUF))
        except IndexError as e:
            pass
        return em
    
    def disambig(self, data, *, WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        pgtitle = data['parse']['title']
        links, descs = zip(*(
          (t.a['href'].lstrip('/wiki'), t.text)
            for t in
          BeautifulSoup(data['parse']['text']['*'], 'lxml').find_all('li')
          ))
        desc = ''.join(f'**{idx}.**{text}' for idx, text in enumerate(descs))
        emb = discord.Embed(title=f'{pgtitle}', url=f'{WIKI_URL}/wiki/{pgtitle.replace(" ", "_")}', description=desc, color=0xffffff)
        return emb, links

    async def handle_page(self, ctx, query, say=None, num=0, *, WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        secs = None
        if say is None:
            msg = say = ctx.send
        async with self.session.get(f'{WIKI_URL}/w/api.php?action=parse&prop=text&format=json&section={num}&page={query}') as resp:
            pgtxt = await resp.text()
        data = json.loads(pgtxt)
        if '(disambiguation)' in data["parse"]["title"]:
            emb, links = self.disambig(data, WIKI_URL=WIKI_URL, API_SUF=API_SUF)
            msg = await say(embed=emb)
            say = msg.edit
            
            def check(rxn, user):
                return user == ctx.message.author and rxn.emoji[0].isdigit() and rxn.message.id == msg.id
                
            for i in range(len(links)):
                if i < 10:
                    await msg.add_reaction(f'{i}\u20E3')
                else:
                    await msg.clear_reactions()
                    await msg.add_reaction(self.bot.get_emoji(371495166277582849))  # :thonk:
                    raise ValueError
            try:
                react, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError as e:
                raise e
            finally:
                await msg.clear_reactions()
            query = links[int(react.emoji[0])]
            async with self.session.get(f'{WIKI_URL}{API_SUF}?action=parse&prop=text&format=json&section={num}&page={query}') as text_resp, \
                       self.session.get(f'{WIKI_URL}{API_SUF}?action=parse&prop=sections&format=json&page={query}') as secs_resp:
                pgtxt = await text_resp.text()
                data = json.loads(pgtxt)
                secs = (await secs_resp.json())["parse"]["sections"]
            secs = [0] + [i["line"].lower() for i in secs if i["line"] not in ('See also', 'References', 'External links')]
            num = 0
        return pgtxt, data, msg, query, num, secs
    
    @mutils.group('Look for a page on conwaylife wiki')
    async def wiki(self, ctx, *, query='', WIKI_URL='http://conwaylife.com', API_SUF='/w/api.php'):
        """
        # Displays a short, nicely-formatted blurb from QUERY's page on http://conwaylife.com/wiki. #
        # Will also display extra info and/or provide pattern files for QUERY, if specified. #

        <[FLAGS]>
        -type: Specifies whether to provide pattern file ("-pat", "-p") or synthesis ("-synth", "-s") from QUERY's page.
          format: Specifies file format for TYPE. Should be any of "rle" (default if omitted), "lif105", "lif106", or "plaintext", but also accepted are "r", "5", "6", and "t".

        <[ARGS]>
        QUERY: Title to search for. If omitted, shows current Pattern of the Week (PoTW) from main page instead.
        """
        if any(i.startswith('-from:') for i in query.split()):
            WIKI_URL = next(i for i in query.split() if i.startswith('-from:')).split(':', 1)[1]
            API_SUF = next((i for i in query.split() if i.startswith('-suf:')), ':/w/api.php').split(':', 1)[1]
            query = ' '.join(i for i in query.split() if not i.startswith(('-from:', '-suf:')))
        if '#' in query:
            query, req_sec = query.split('#', 1) # 'requested_section'
            req_sec = req_sec.lower()
        else:
            req_sec = 0
        if query[:1].lower() + query[1:] == 'caterer':
            await ctx.message.add_reaction('👋')
        await ctx.channel.trigger_typing()
        em = discord.Embed()
        em.color = 0x000000
        
        if query[:1].lower() + query[1:] == 'methusynthesis':
            em.set_footer(text=f'(redirected from "{query}")')
            query = 'methusynthesae'
        if query[:1].lower() + query[1:] == 'methusynthesae':
            em.title = 'Methusynthesae'
            em.description = "**Methusynthesae** are patterns/methuselah that basically/mildly are spaceship reactions, though it is a bit hard to explain the relation. It is way different from syntheses because they *are* patterns, and **don't** form other patterns."
            em.url = 'http://conwaylife.com/forums/viewtopic.php?f=2&t=1600'
            em.set_thumbnail(url='attachment://methusynthesis1.png')
            return await ctx.send(file=discord.File('./cogs/resources/methusynthesis1.png', 'methusynthesis1.png'), embed=em)
        
        if not query: # get pattern of the week instead
            async with self.session.get(f'{WIKI_URL}{API_SUF}?action=parse&prop=text&format=json&section=0&page=Main_Page') as resp:
                data = await resp.text()
            
            pgtxt = json.loads(data)["parse"]["text"]["*"]
            pgtxt = pgtxt.split("/Snippet")[0]; query = pgtxt.split(pgtxt.rindex(" "))[1] # this line is an extremely lazy workaround
            """
            data = data.split('Download.')[0]
            try:
                pgimg = (rPGIMG.search(data) or rPGIMGFALLBACK.search(data) or rTHUMB.search(data)).group()
            except AttributeError:
                pass
            else:
                em.set_thumbnail(url=f'{WIKI_URL}{pgimg}')
            info = rPOTW.search(pgtxt)
            em.title="This week's featured article"
            em.url = f'{WIKI_URL}{info.group(1)}' # pgtitle=info.group(2)
            em.description = self.clean(pgtxt.split('a></div>')[1].split('<div align')[0], potw=True, WIKI_URL=WIKI_URL, API_SUF=API_SUF)
            return await ctx.send(embed=em)"""
        
        async with self.session.get(f'{WIKI_URL}{API_SUF}?action=parse&prop=text&format=json&section=0&page={query}') as resp:
            prelim = await resp.text()
        if '>REDIRECT ' in prelim:
            query = rREDIRECT.search(prelim).group(1)
        elif 'missingtitle' in prelim or 'invalidtitle' in prelim:
            return await ctx.send(f'Page `{query}` does not exist.') # no sanitization yeet
        
        async with self.session.get(f'{WIKI_URL}{API_SUF}?action=parse&prop=sections&format=json&page={query}') as resp:
            secs = json.loads(await resp.text())["parse"]["sections"]
        
        secs = [0] + [i["line"].lower() for i in secs if i["line"] not in ('See also', 'References', 'External links')]
        num = secs.index(req_sec) if req_sec in secs else 0
        
        try:
            pgtxt, data, blurb, query, num, secs_ = await self.handle_page(ctx, query, num=num, WIKI_URL=WIKI_URL, API_SUF=API_SUF)
            say = blurb.edit if blurb != ctx.send else ctx.send
        except (ValueError, IndexError, asyncio.TimeoutError) as e:
            return
        else:
            if secs_ is not None:
                secs = secs_
        
        seclist = [None] * len(secs)
        seclist[num] = pgtxt, data
        
        pgtxt = pgtxt.split('Category:' if 'Category:' in pgtxt else '/table')[0]
        pgimg = rPGIMG.search(pgtxt) or rPGIMGFALLBACK.search(pgtxt) or rTHUMB.search(pgtxt)
        pgimg = pgimg.group() if pgimg else None
        em = await self.regpage(data, query, em, pgimg, WIKI_URL=WIKI_URL, API_SUF=API_SUF)
        
        nav = ['🔼', '🔽'] if num else ['🔽']
        panes = ['📝', '🔧']; cur_pane = 0, '🗒'
        ptypes = ['🇷', '🇨', '5⃣', '6⃣']
        
        def check(rxn, usr):
            return rxn.emoji in nav + panes and usr is ctx.message.author and rxn.message.id == blurb.id
        
        try:
            said, synthfile, rle = False, None, None
            while True:
                if not said:
                    _ = await say(content=None, embed=em)
                    if _ is not None:
                        blurb = _
                        say = blurb.edit
                [await blurb.add_reaction(i) for i in (nav if not said else [])+panes]
                said = False
                reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
                await blurb.clear_reactions()
                if reaction.emoji in nav or reaction.emoji == '🗒':
                    try:
                        num += 1 - 2 * ['🔽', '🔼'].index(reaction.emoji)
                    except ValueError as e:
                        panes.insert(*cur_pane)
                        cur_pane = panes.index(reaction.emoji), reaction.emoji
                        panes.remove(reaction.emoji)
                    else:
                        if num >= len(secs):
                            num, nav = len(secs), ['🔼']
                        elif num <= 0:
                            num, nav = 0, ['🔽']
                        else:
                            nav = ['🔼', '🔽']
                    
                    if seclist[num] is not None:
                        pgtxt, data = seclist[num]
                    else:
                        pgtxt, data, *_ = await self.handle_page(ctx, query, num=num, WIKI_URL=WIKI_URL, API_SUF=API_SUF)
                        seclist[num] = pgtxt, data
                    em = await self.regpage(data, query, discord.Embed(), pgimg, suffix=f' ({secs[num]})' if num else '', WIKI_URL=WIKI_URL, API_SUF=API_SUF)
                    continue
                # else reaction.emoji must be in panes
                if reaction.emoji == 'ℹ': # info (TODO)
                    continue
                panes.insert(*cur_pane)
                cur_pane = panes.index(reaction.emoji), reaction.emoji
                panes.remove(reaction.emoji)
                if reaction.emoji == '📝': # pattern file
                    if None in (rle, seclist[0]):
                        seclist[0] = (await self.handle_page(ctx, query, num=0, WIKI_URL=WIKI_URL, API_SUF=API_SUF))[:2]
                        rle = await self.send_info(ctx, seclist[0][0], query, 'pat', say, filetype=re.escape('.rle'), send=False)
                    await say(content=rle, embed=None)
                if reaction.emoji == '🔧': # glider synth
                    if None in (synthfile, seclist[0]):
                        seclist[0] = (await self.handle_page(ctx, query, num=0, WIKI_URL=WIKI_URL, API_SUF=API_SUF))[:2]
                        synthfile = await self.send_info(ctx, seclist[0][0], query, 'synth', say, filetype=r'\.\w+', send=False)
                    await say(content=synthfile, embed=None)
                said = True
        
        finally:
            await blurb.clear_reactions()
    
    @mutils.command('Provide a Did-You-Know fact from wiki')
    async def dyk(self, ctx, *nums: int):
        """# Provides either a random Did-You-Know fact from wiki or else any number of specific DYKs. #

        <[ARGS]>
        NUM: Specific DYK(s) to display. If omitted, displays a single random DYK instead.
        [or]
        SEARCH: Triggered automatically if input is not a number, and displays DYKs containing given text. To search for a number, prefix it with a single period; .12, for instance, searches for DYKs containing "12".
        """
        nums = nums or [random.randint(0, wiki_dyk.count - 1)]
        em = discord.Embed(title='Did you know...\n', description='', color=0xffffff)
        for item in ((n-1) % wiki_dyk.count if n else wiki_dyk.count - 1 for n in nums):
            em.description += f'**#{item + 1}:** {wiki_dyk.trivia[item]}\n'
        await ctx.send(embed=em)
    
    @dyk.error
    async def dyk_search(self, ctx, error):
        # is it bad practice to abuse the error handler like this? ...probably
        if isinstance(error, commands.BadArgument):
            em = discord.Embed(title='Did you know...\n', description='', color=0xffffff)
            # remove invocation from message and keep query, since we can't do ctx.args here
            query = ctx.message.content.split(' ', 1)[1].rstrip()
            query = query[len(query) > 1 and query[0] == '.' and query[1:].isdigit():] # allow searching for numbers by prepending a period
            rquery = re.compile(fr'\b{re.escape(query)}\b', re.I)
            matches = [wiki_dyk.plaintext.index(i) for i in wiki_dyk.plaintext if rquery.search(i)]
            if not matches:
                return await ctx.send(f'No results found for `{query}`.')
            for item in matches[:3]:
                em.description += f'**#{1+item}:** {wiki_dyk.trivia[item]}\n'
            em.set_footer(text=f'Showing first three or fewer DYK results for "{query}"')
            return await ctx.send(embed=em)
        raise error
    
    @staticmethod
    def normalized_filetype(filetype):
        filerefs = {('5', '105', 'l105', 'lif105'): '_105.lif', ('6', '106', 'l106', 'lif106'): '_106.lif', ('r', 'rle', 'RLE'): '.rle', ('t', 'plaintext', 'text', 'cells'): '.cells'}
        normalized = filetype.strip('.').lower()
        return [filerefs[v] for v in filerefs if normalized in v][0] if any(normalized in v for v in filerefs) else (filetype,)
    
    @staticmethod
    def normalized_query(query):
        return query[0].upper() + query[1:]
    
    async def send_info(self, ctx, pgtxt, query, caller, say, filetype, send=True):
        notfound = {r'\.rle': 'RLE', r'\.cells': 'plaintext', r'_105\.lif': 'Life 1.05', r'_106\.lif': 'Life 1.06'}.get(filetype, filetype)
        search = {'pat': (' Pattern files', f'{notfound} pattern file', 'Pattern files'), 'synth': ('>Glider synthesis<', 'glider synthesis')}
        if search[caller][0] in pgtxt:
            rpat = re.compile(fr'http://www\.conwaylife\.com/patterns/[\w\-. ]+?{filetype}', re.I)
            patfile = rpat.search(pgtxt.split('Pattern files', 1)[-(caller=='pat')])
            
            if patfile:
                async with self.session.get(patfile.group()) as resp:
                    msgtext = '```makefile\n{}```'.format(await resp.text())
            else:
                msgtext = f'Page `{query}` has no {search[caller][1]}.'
        else:
            msgtext = f'Page `{query}` lists no {search[caller][1]}.'
        try:
            if send:
                await say(content=msgtext, embed=None)
            else:
                return msgtext
        except discord.errors.HTTPException as e:
            if send:
                await say(content=f'Page `{query}` either has no {search[caller][1]} or its file is too large to send via Discord.', embed=None)
            else:
                return f'Page `{query}` either has no {search[caller][1]} or its file is too large to send via Discord.'
    
    @wiki.command(name='-pat')
    async def pat(self, ctx, filetype: normalized_filetype, *, query=''):
        async with ctx.typing():
            if isinstance(filetype, tuple):
                query = f'{filetype[0]} {query}'
                filetype = '.rle'
            try:
                pgtxt, data, msg = await self.handle_page(ctx, query)
                say = msg.edit if msg != ctx.send else ctx.send
            except (ValueError, IndexError, asyncio.TimeoutError) as e:
                return
            
            query = self.normalized_query(query)
            await self.send_info(ctx, pgtxt, query, 'pat', say, re.escape(filetype))
    
    
    @wiki.command(name='-synth')
    async def synth(self, ctx, *, query):
        async with ctx.typing():
            try:
                pgtxt, data, msg = await self.handle_page(ctx, query)
                say = msg.edit if msg != ctx.send else ctx.send
            except (ValueError, IndexError, asyncio.TimeoutError) as e:
                return
            
        query = self.normalized_query(query)
        await self.send_info(ctx, pgtxt, query, 'synth', say, filetype=r'\.\w+')  

def setup(bot):
    bot.add_cog(Wiki(bot))
