#encoding: utf-8

args = {
  'dyk': '+num / >search',
  'help': '>cmd',
  'sim': 'gen ?step ?rule ?pat (-h -tag -time(:all) -id:identifier)',
  'sim rand': 'gen ?dims ?step ?rule (-include:n,n..m,n..m+s -exclude:n,n..m,n..m+s -h -tag -time(:all) -id:identifier)',
  'rules': '?name / ?member',
  'todo': '*cmd',
  'upload': 'name >blurb',
  'register': 'name ?>blurb',
  'wiki': '?+query (-type:?format)',
}

# ---------- #

aliases = {
  'new': ['changes', 'changelog', 'whatsnew'],
  'info': ['about', 'what'],
  'link': ['invite', 'url'],
  'rules': ['rule'],
  'sim': ['gif'],
  'sim rand': ['r', 'random'],
  'generators': ['gens', 'generator', 'gen'],
  'todo': ['todos'],
  'todo add': ['new'],
  'todo del': ['rm', 'remove', 'delete'],
  'todo move': ['mv', 'mov'],
  'todo complete': ['fi', 'finish']
}
