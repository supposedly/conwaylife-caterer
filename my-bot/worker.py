import discord
import json
import asyncio
import re
import requests
from html import unescape
from collections import namedtuple
from json import load

rbold = re.compile(r"<b>|</b>") # this takes WAYWAYWAYWAYWAY too many steps, use data.replace('<b>', '**').replace('</b>', '**') instead
rparens = re.compile(r" [\([].+?[\)\]]") # brackets too
rtags = re.compile(r"<.+?>")
rctrlchars = re.compile(r"\\.") # needs to be changed maybe
rfirstpbreak = re.compile(r"<p>.+?</p>") # too slow, use strn.split('<p>', 1)[1].split('</p>')[0] instead
rredirect = re.compile(r">(.+?)</a>")

rgif = re.compile(r"File[^F]+?\.gif")
rimage = re.compile(r"File[^F]+?\.png")

rdisamb = re.compile(r"(?<=\*\*).+(?=\*\*)")
rlinksb = re.compile(r"^\[\[(.*?)(\|)?(?(2)(.*?))\]\]", re.M)

numbers_ft = [':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:']
numbers_fu = [u'\u0031\u20E3', u'\u0032\u20E3', u'\u0033\u20E3', u'\u0034\u20E3', u'\u0035\u20E3', u'\u0036\u20E3', u'\u0037\u20E3', u'\u0038\u20E3', u'\u0039\u20E3']
#numbers_rt = {':one:': 1, ':two:': 2, ':three:': 3, ':four:': 4, ':five:': 5, ':six:': 6, ':seven:': 7, ':eight:': 8, ':nine:': 9}
numbers_ru = {u'\u0031\u20E3': 0, u'\u0032\u20E3': 1, u'\u0033\u20E3': 2, u'\u0034\u20E3': 3, u'\u0035\u20E3': 4, u'\u0036\u20E3': 5, u'\u0037\u20E3': 6, u'\u0038\u20E3': 7, u'\u0039\u20E3': 8}

links = []

def parse(txt):
    txt = txt.replace('<b>', '**').replace('</b>', '**')
    txt = txt.split('<p>', 1)[1].split('</p>')[0]
    txt = rparens.sub('', txt)
    txt = rtags.sub('', txt)
    txt = rctrlchars.sub('', txt)
    return txt

def regpage(jdata, data, query, rqst, em):
    images = rqst.get("http://conwaylife.com/w/api.php?action=query&prop=images&format=json&titles=" + query).text
    pgimg = rgif.search(images)
    find = rimage.findall(images)
    pgimg = (pgimg.group(0) if pgimg else (min(find, key = len) if find else ''))
    images = rqst.get("http://conwaylife.com/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles=" + pgimg).text
    pgimg = rfileurl.search(images)
    if pgimg:
        pgimg = pgimg.group(1)
        em.set_thumbnail(url=pgimg)

    pgtitle = jdata["parse"]["title"]
    desc = unescape(parse(jdata["parse"]["text"]["*"]))

    em.title = pgtitle
    em.url = "http://conwaylife.com/wiki/" + pgtitle.replace(" ", "_")
    em.description = desc
    em.color = 0x680000

def parsedisambig(txt):
    txt = rformatting.sub('', txt)
    txt = rrefs.sub('', txt)
    txt = txt.replace('* ', '')
    txt = rlinksb.sub(lambda m: '**' + (m.group(3) if m.group(3) else m.group(1)) + '**', txt)
    txt = rlinks.sub(lambda m: m.group(3) if m.group(3) else m.group(1), txt)
    txt = rfinal.sub('', txt)
    links = rdisamb.findall(txt)
    return (txt, links)

def disambig(data):
    pgtitle = rtitle.search(data).group(1)
    desc_links = parsedisambig(data)
    return (discord.Embed(title=pgtitle, url='http://conwaylife.com/wiki/' + pgtitle.replace(' ', '_'), description=desc_links[0], color=0x680000), desc_links[1])

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    if message.content.startswith("!wiki"):
        em = discord.Embed()
        edit = False
        query = message.content[6:]
        if query == "methusynthesae" or query == "Methusynthesae":
            gus = "Methusynthesae (singular Methusynthesis) are patterns/methuselah that basically/mildly are spaceship reactions, though it is a bit hard to explain the relation. It is way different from syntheses because they are patterns, and don't form other patterns."
            em = discord.Embed(title="Methusynthesae", description=gus, color=0x680000, url='http://conwaylife.com/forums/viewtopic.php?f=2&t=1600')
            em.set_thumbnail(url='https://i.imgur.com/CQefDXF.png')
            await client.send_message(message.channel, embed=em)
        else:
            with requests.Session() as rqst:
                data = rqst.get("http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=" + query).text
                
                if '#REDIRECT' in data:
                    em.set_footer(text='(redirected from "' + query + '")')
                    query = rredirect.search(data).group(1)
                    data = rqst.get("http://conwaylife.com/w/api.php?action=parse&prop=text&format=json&section=0&page=" + query).text
                    
                if 'missingtitle' in data:
                    await client.send_message(message.channel, 'Page `' + query + '` does not exist.')
                else:
                    jdata = json.loads(data)
                    if "(disambiguation)" in data:
                        edit = True
                        data = data.replace(r'\n', '\n')
                        emb = disambig(data)
                        links = emb[1]
                        emb = emb[0]
                        msg = await client.send_message(message.channel, embed=emb)
                        for i in range(len(links)):
                            await client.add_reaction(msg, numbers_fu[i])
                        react = await client.wait_for_reaction(numbers_fu, message=msg, user=message.author)
                        query = links[numbers_fu.index(react.reaction.emoji)]
                        data = rqst.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles=" + query).text
                    
                    regpage(jdata, data, query, rqst, em)
                    if edit:
                        await client.edit_message(msg, embed=em)
                        await client.clear_reactions(msg)
                    else:
                        await client.send_message(message.channel, embed=em)


client.run('MzU5MDY3NjM4MjE2Nzg1OTIw.DKBnUw.MJm4R_Zz6hCI3TPLT05wsdn6Mgs')

