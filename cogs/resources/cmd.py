#encoding: utf-8

args = {
  "dyk": '+num / >search',
  "help": '>cmd',
  "sim": 'gen ?step ?rule ?pat (-h -tag -time(:all) -id:identifier)',
  "sim rand": 'gen ?dims ?step ?rule (-h -tag -time(:all) -id:identifier)',
  "rules": '?name / ?member',
  "todo": '*cmd',
  "upload": '>blurb',
  "register": 'name >blurb',
  "wiki": '?+query (-type:?format)',
}

# ---------- #

aliases = {
  "new": ['changes', 'changelog', 'whatsnew'],
  "info": ['about', 'what'],
  "link": ['invite', 'url'],
  "sim": ['gif'],
  "sim rand": ['r', 'random'],
  "todo": ['todos'],
  "todo add": ['new'],
  "todo del": ['rm', 'remove', 'delete'],
  "todo move": ['mv', 'mov'],
  "todo complete": ['fi', 'finish']
}
