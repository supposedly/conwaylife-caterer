#encoding: utf-8
desc = {
"help": '''# A prettified sort of help command — because HelpFormatter is for dweebs. #

<[ARGS]>
CMD: Command to display usage info for. If ommitted or invalid, displays generic help/info message.''',

"info": '''# Displays credits, useful links, and information about this bot's dependencies. #''',

"wiki": '''# Displays a small, nicely-formatted blurb from QUERY's page including image, title, and rеdirеct handling. #
# Will also display extra info and/or provide pattern files for QUERY, if specified. #

<[FLAGS]>
TYPE: Specifies whether to provide pattern file ("pat", "p") or synthesis ("synth", "s") from QUERY's page.
FORMAT (optional): Specifies file format for TYPE. Must be any of "rle" (default), "lif105", "lif106", or "plaintext".

<[ARGS]>
QUERY: Title to search for оn http://conwaylife.com/wiki. If disambiguated, displays options with reaction UI allowing user to navigate to intended page.

#TODO: no arguments displays PoTW, allow subsection links, implement flags''',

"dyk": '''# Provides either a random Did-You-Know fact from wiki or else any number of specific DYKs. #

<[ARGS]>
NUM: Specific DYK(s) to display. If omitted, displays a single random DYK instead.''',

"sim": '''# Currently under construction. Simulates PAT with output to animated gif. #

<[FLAGS]>
r (rand): Simulate a random soup in given rule, default 16x16 but can be specified. Precludes PAT.
    x, y: Width and height of generated soup.

<[ARGS]>
GEN (required): Generation to simulate up to.
STEP: Step size. Affects simulation speed. If ommitted, defaults to 1.
RULE: Rulestring to simulate PAT under. If ommitted, defaults to B3/S23 or rule specified in PAT.
PAT: One-line rle or .lif file to simulate. If ommitted, uses last-sent Golly-compatible pattern (which should be enclosed in a code block and therefore can be a multiliner).

#TODO: streamline GIF generation process, implement proper LZW compression, implement flags & especially gfycat upload''',

"link": '''# Produces an oauth2 invite link for this bot with necessary permissions. #''',

"no": '''# no #'''
}

# ---------- #

args = {
"help": '*CMD',

"info": '',

"wiki": '(type *format) QUERY',

"dyk": '**NUM',

"sim": '(rand *x *y) (gfy) (track) GEN *STEP *RULE *PAT',

"link": '',

"no": ''
}

# ---------- #

aliases = {
"help": [],

"info": ['what'],

"wiki": [],

"dyk": [],

"sim": ['gif'],

"sim.rand": ['r', 'R'],

"link": ['invite', 'url'],

"no": []
}
