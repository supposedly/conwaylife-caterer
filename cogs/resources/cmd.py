#encoding: utf-8
desc = {
"help": '''# A prettified sort of help command — because HelpFormatter is for dweebs. #

<[ARGS]>
CMD: Command to display usage info for. If ommitted or invalid, displays generic help/info message.''',

"info": '''# Displays credits, useful links, and information about this bot's dependencies. #''',

"wiki": '''# Displays a short, nicely-formatted blurb from QUERY's page on http://conwaylife.com/wiki. #
# Will also display extra info and/or provide pattern files for QUERY, if specified. #

<[FLAGS]>
type: Specifies whether to provide pattern file ("pat", "p") or synthesis ("synth", "s") from QUERY's page.
    format: Specifies file format for TYPE. Must be any of "rle" (default), "lif105", "lif106", or "plaintext".

<[ARGS]>
QUERY: Title to search for. If omitted, shows current Pattern of the Week (PoTW) instead.

#TODO: allow subsection links, implement flags''',

"dyk": '''# Provides either a random Did-You-Know fact from wiki or else any number of specific DYKs. #

<[ARGS]>
NUM: Specific DYK(s) to display. If omitted, displays a single random DYK instead.
[or]
QUERY: If given a word instead of a number, searches for text in DYKs. To search for a number instead of NUM, prefix it with a period; .12, for instance, searches for DYKs containing "12".''',

"sim": '''# Currently under construction. Simulates PAT with output to animated gif. #

<[FLAGS]>
r (rand): Simulate a random soup in given rule, default 16x16 but can be specified. Precludes PAT.
    x: Width of generated soup.
    y: Height.

<[ARGS]>
GEN (required): Generation to simulate up to.
STEP: Step size. Affects simulation speed. If ommitted, defaults to 1.
RULE: Rulestring to simulate PAT under. If ommitted, defaults to B3/S23 or rule specified in PAT.
PAT: One-line rle or .lif file to simulate. If ommitted, uses last-sent Golly-compatible pattern (which should be enclosed in a code block and therefore can be a multiliner).

#TODO: streamline GIF generation process, implement proper LZW compression, implement flags besides rand & especially gfycat upload''',

"link": '''# Produces an oauth2 invite link for this bot with necessary permissions. #''',

"no": '''# no #''',

"yes": '''# yes? #'''
}

# ---------- #

args = {
"help": '*CMD',

"info": '',

"wiki": '(type *format) *QUERY',

"dyk": '**NUM / *QUERY',

"sim": '(rand *x *y) (gfy) (track) GEN *STEP *RULE *PAT',

"link": '',

"no": '',

"yes": ''
}

# ---------- #

aliases = {
"help": [],

"info": ['about', 'what'],

"wiki": [],

"dyk": [],

"sim": ['gif'],

"sim.rand": ['r', 'R'],

"link": ['invite', 'url'],

"no": [],

"yes": []
}
