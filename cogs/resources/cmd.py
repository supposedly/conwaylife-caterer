#encoding: utf-8

args = {
  'dyk': '+num / >search',
  'help': '>cmd',
  'sim': 'gen ?step ?rule ?pat (-h -tag -time(:all) -id:identifier)',
  'sim rand': 'gen ?dims ?step ?rule (-include:n,n..m,n..m+s -exclude:n,n..m,n..m+s -h -tag -time(:all) -id:identifier)',
  'generate_apgtable': 'rulestring rulename',
  'rules': '?name / ?member',
  'todo': '*cmd',
  'upload': 'name >blurb',
  'register': 'name ?>blurb',
  'wiki': '?+query (-type:?format)',
  '5s': 'velocity',
  'sossp': 'period'
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
  'generate_apgtable': ['apgtable'],
  'sssss': ['5s'],
  'todo': ['todos'],
  'todo add': ['new'],
  'todo del': ['rm', 'remove', 'delete'],
  'todo move': ['mv', 'mov'],
  'todo complete': ['fi', 'finish']
}
