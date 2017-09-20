import discord
import asyncio
import re
import requests

def regex(txt):
    txt = re.sub(r"'''", r"**", txt)
    txt = re.sub(r" \(.+?\)", r"", txt)
    txt = re.sub(r"<.+?>", r"", txt)
    txt = re.sub(r"\[\[(.*?)(\|)?(?(2)(.*?))\]\]", lambda m: m.group(3) if m.group(3) else m.group(1), txt)
    txt = re.sub(r"{.+?}}", r"", txt)
    txt = re.sub(r"\\.", r"", txt)
    txt = re.sub(r"=.*", r"", txt)
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
            query = re.search(r'\[\[(.+?)\]\]', data).group(1)
            em.set_author(name='Redirect:')
            data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
            #await client.send_message(message.channel, 'This redirects to `' + query + '`')
            data = requests.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles="+query).text
        
        pgtitle = re.search(r'"title":"(.+?)",', data).group(1)
        desc = regex(data)
        data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
        
        em.title = pgtitle
        em.url = "http://conwaylife.com/wiki/"+query.replace(" ", "_")
        em.description = desc
        em.color = 0x680000
        
        await client.send_message(message.channel, embed=em)

client.run('MzU5MDY3NjM4MjE2Nzg1OTIw.DKBnUw.MJm4R_Zz6hCI3TPLT05wsdn6Mgs')
