import discord
import asyncio
import re
import requests
from html import unescape

rbold = re.compile(r"'''")
rparens = re.compile(r" \(.+?\)")
rtags = re.compile(r"<.+?>")
rlinks = re.compile(r"\[\[(.*?)(\|)?(?(2)(.*?))\]\]")
rformatting = re.compile(r"{.+?}}")
rctrlchars = re.compile(r"\\.")
#rfirstheader = re.compile(r"=.*")
rfirstpbreak = re.compile(r"\\n\\n.*")

rtitle = re.compile(r'"title":"(.+?)",')

def regex(txt):
    txt = rbold.sub('**', txt)
    txt = rparens.sub('', txt)
    txt = rtags.sub('', txt)
    txt = rlinks.sub(lambda m: m.group(3) if m.group(3) else m.group(1), txt)
    txt = rformatting.sub('', txt)
    txt = rfirstpbreak.sub('', txt) # exchange with rfirstheader.sub() below for entire first section to be preserved
    txt = rctrlchars.sub('', txt)
#   txt = rfirstheader.sub('', txt)
    return txt

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    em = discord.Embed()
    if message.content.startswith("!wiki"):
    
        query = message.content[6:]
        data = requests.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles="+query).text
        
        if '#REDIRECT' in data:
            em.set_footer(text='(redirected from "' + query + '")')
            query = re.search(r'\[\[(.+?)\]\]', data).group(1)
            data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
            #await client.send_message(message.channel, 'This redirects to `' + query + '`')
            data = requests.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles="+query).text
            
        if "There is currently no text in this page." in data:
            await client.send_message('Page "' + query + '" does not exist.')
        else:
            pgtitle = rtitle.search(data).group(1)
            desc = unescape(regex(data))
            data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
            
            em.title = pgtitle
            em.url = "http://conwaylife.com/wiki/"+query.replace(" ", "_")
            em.description = desc
            em.color = 0x680000
            
            await client.send_message(message.channel, embed=em)

client.run('MzU5MDY3NjM4MjE2Nzg1OTIw.DKBnUw.MJm4R_Zz6hCI3TPLT05wsdn6Mgs')
