import discord
import json
import asyncio
import re
import requests
from html import unescape
from collections import namedtuple
from json import load

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

rparens = re.compile(r" \(.+?\)")
rbracks = re.compile(r"\[.+?\]")
rtags = re.compile(r"<.+?>", re.S)
rredherring = re.compile(r"<p>.{0,10}</p>", re.S) #to prevent `<p><br />\n</p> as in the Simkin Glider Gun page, stupid hack
rctrlchars = re.compile(r"\\.") #needs to be changed maybe
rredirect = re.compile(r'">(.+?)</a>')

rgif = re.compile(r"File[^F]+?\.gif")
rimage = re.compile(r"File[^F]+?\.png")

rlinks = re.compile(r"<li> ?<a href.+?>(.+?)</a>")
rlinksb = re.compile(r"<a href.+?>(.+?)</a>")
rdisamb = re.compile(r'<li> ?<a href="/wiki/(.+?)"')

rnewlines = re.compile(r"\n+")

numbers_fu = [u'\u0031\u20E3', u'\u0032\u20E3', u'\u0033\u20E3', u'\u0034\u20E3', u'\u0035\u20E3', u'\u0036\u20E3', u'\u0037\u20E3', u'\u0038\u20E3', u'\u0039\u20E3']

def parse(txt):
    txt = rredherring.sub('', txt)
    txt = txt.replace('<b>', '**').replace('</b>', '**').split('<p>', 1)[1].split('</p>')[0]
    txt = rtags.sub('', txt)
    txt = rctrlchars.sub('', txt)
    txt = rparens.sub('', txt)
    txt = rbracks.sub('', txt)
    return txt

def regpage(data, query, rqst, em):
    images = rqst.get("http://conwaylife.com/w/api.php?action=query&prop=images&format=json&titles=" + query).text
    pgimg = rgif.search(images)
    find = rimage.findall(images)
    pgimg = (pgimg.group(0) if pgimg else (min(find, key = len) if find else ''))
    images = json.loads(rqst.get("http://conwaylife.com/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles=" + pgimg).text)
    try:
        pgimg = list(images["query"]["pages"].values())[0]["imageinfo"][0]["url"]
        em.set_thumbnail(url=pgimg)
    except (KeyError, TypeError):
        pass

    pgtitle = data["parse"]["title"]
    desc = unescape(parse(data["parse"]["text"]["*"]))

    em.title = pgtitle
    em.url = "http://conwaylife.com/wiki/" + pgtitle.replace(" ", "_")
    em.description = desc

def parsedisambig(txt):
    txt = txt.replace('<b>', '').replace('</b>', '')
    # think ^ should stay this way so the title doesn't clash visually with the options, but ('' --> '**') if you ever wanna change it in the future
    links = rdisamb.findall(txt)
    txt = rlinks.sub(lambda m: '**' + m.group(1) + '**', txt)
    txt = rlinksb.sub(lambda m: m.group(1), txt)
    
    txt = rtags.sub('', txt)
    
    txt = rnewlines.sub('\n', txt)
    return (txt, links)

def disambig(data):
    pgtitle = data["parse"]["title"]
    desc_links = parsedisambig(data["parse"]["text"]["*"])
    return (discord.Embed(title=pgtitle, url='http://conwaylife.com/wiki/' + pgtitle.replace(' ', '_'), description=desc_links[0], color=0xffffff), desc_links[1])

@client.event
async def on_message(message):

    if message.content.startswith("!invite" if message.server.id == '357922255553953794' else "ca.invite"):
        em = discord.Embed(color=0x000000)
        em.set_author(name=r'\', icon_url=client.user.avatar_url)
        em.add_field(url=discord.utils.oauth_url(client.user.id, permissions=discord.Permissions(permissions=52288)), title='Use this link to invite me to your server!')
        await client.send_message(message.channel, embed=em)
    
    if message.content.startswith("!wiki" if message.server.id == '357922255553953794' else "ca.wiki"):
    
        em = discord.Embed()
        em.color = 0x000000
        
        edit = False
        query = message.content[6:]
        if query[:1].lower() + query[1:] == 'methusynthesis':
            em.set_footer(text='(redirected from "' + query + '")')
            query = "methusynthesae"
        if query[:1].lower() + query[1:] == 'methusynthesae':
            gus = "**Methusynthesae** are patterns/methuselah that basically/mildly are spaceship reactions, though it is a bit hard to explain the relation. It is way different from syntheses because they are patterns, and don't form other patterns."
            em.title = 'Methusynthesae'
            em.description = gus
            em.url = 'http://conwaylife.com/forums/viewtopic.php?f=2&t=1600'
            em.set_thumbnail(url='https://i.imgur.com/CQefDXF.png')
            await client.send_message(message.channel, embed=em)
        else:
            with requests.Session() as rqst:
                data = rqst.get("http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=" + query).text
                
                if '>REDIRECT ' in data:
                    em.set_footer(text='(redirected from "' + query + '")')
                    query = rredirect.search(data).group(1)
                    data = rqst.get("http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=" + query).text
                    
                if 'missingtitle' in data:
                    await client.send_message(message.channel, 'Page `' + query + '` does not exist.')
                else:
                    data = json.loads(data)
                    if "(disambiguation)" in data["parse"]["title"]:
                        edit = True
                        emb = disambig(data)
                        links = emb[1]
                        emb = emb[0]
                        msg = await client.send_message(message.channel, embed=emb)
                        for i in range(len(links)):
                            await client.add_reaction(msg, numbers_fu[i])
                        react = await client.wait_for_reaction(emoji=numbers_fu, message=msg, user=message.author)
                        query = links[numbers_fu.index(react.reaction.emoji)]
                        data = json.loads(rqst.get("http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=" + query).text)
                    
                    regpage(data, query, rqst, em)
                    if edit:
                        await client.edit_message(msg, embed=em)
                        await client.clear_reactions(msg)
                    else:
                        await client.send_message(message.channel, embed=em)


client.run('MzU5MDY3NjM4MjE2Nzg1OTIw.DKBnUw.MJm4R_Zz6hCI3TPLT05wsdn6Mgs')

