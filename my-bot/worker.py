import discord
import asyncio
import re
import requests

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
        query = message.content[6:]
        #await client.send_message(message.channel, "copy that: " + query)
        data = requests.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles="+query).text
        if '#REDIRECT' in data:
            query = re.search(r'\[\[(.+?)\]\]', data).group(1)
            data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
            await client.send_message(message.channel, 'This redirects to `' + query + '`')
            data = requests.get("http://conwaylife.com/w/api.php?action=query&prop=revisions&rvprop=content&format=json&titles="+query).text
        desc = data
        data = requests.post(url='http://conwaylife.com/w/api.php', headers={'Connection':'close'})
        
        pgtitle = re.search(r'"title":"(.+?)",', desc).group(1)
        
        desc = re.sub(r"'''", r"**", desc)
        desc = re.sub(r" \(.+?\)", r"", desc)
        desc = re.sub(r"<.+?>", r"", desc)
        desc = re.sub(r"\[\[(.*?)(\|)?(?(2)(.*?))\]\]", lambda m: m.group(3) if m.group(3) else m.group(1), desc)
        desc = re.sub(r"{.+?}}", r"", desc)
        desc = re.sub(r"\\.", r"", desc)
        desc = re.sub(r"=.*", r"", desc)
        #await client.send_message(message.channel, "desc: " + desc)
        em = discord.Embed(title=pgtitle, url="http://conwaylife.com/wiki/"+query.replace(" ", "_"), description=desc, color=0x680000)
        em.set_author(name='Someone', icon_url=client.user.default_avatar_url)
        await client.send_message(message.channel, embed=em)

client.run('MzU5MDY3NjM4MjE2Nzg1OTIw.DKBnUw.MJm4R_Zz6hCI3TPLT05wsdn6Mgs')
