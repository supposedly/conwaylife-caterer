import asyncio
import concurrent
import copy
import io
import json
import math
import marshal
import operator
import os
import random
import re
import sys
import time
import types
import subprocess
from ast import literal_eval
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum
from itertools import count, islice, starmap

import aiofiles
import discord
import imageio
import png
import numpy as np
from discord.ext import commands
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

from cogs.resources import mutils


class Log:
    __slots__ = 'invoker', 'rule', 'time', 'status'

    def __init__(self, invoker, rule, time, status):
        self.invoker = invoker
        self.rule = rule
        self.time = time
        self.status = status


class Status(Enum):
    WAITING = 0
    SIMMING = 1
    CANCELED = 2
    COMPLETED = 3
    FAILED = 4


# MOD_ROLE_IDS = {
#   441021286253330432,  # admin
#   358487842755969025,  # mod
#   431273609567141889,  # tempmod
#   }

WRIGHT = 180809886374952960
ASSETS = 424383992666783754
BOTS_N_MUTE = 404518331605975040
ROOT_2 = 2 ** 0.5

# matches LtL rulestring
rLtL = re.compile(r'R\d{1,3},C(\d{1,3}),M[01],S\d+\.\.\d+,B\d+\.\.\d+,N[NM]', re.I)

# matches either W\d{3} or B/S, and then if no B then either 2-state single-slash rulestring or generations rulestring
rRULESTRING = re.compile(
    r'MAP(?:[A-Z0-9+/]{86}|[A-Z0-9+/]{22}|[A-Z0-9+/]{6})'  # MAP rules
    r'|W\d{3}'  # Wolfram 1D rules
    r'|/?(?:(B)?(?:[0-8]-?[cekainyqjrtwz]*)+(?(1)/?(S)?(?:[0-8]-?[cekainyqjrtwz]*)*|/(S)?(?:[0-8]-?[cekainyqjrtwz]*)*(?(2)|(?(3)|/[\d]{1,3})?)))[HV]?',
    re.I
)

# matches CAViewer's supported rulespaces
rCAVIEWER = ""
lst = open(os.path.dirname(os.path.abspath(__file__)) + "/resources/regex.txt", "r").readlines()
for i in range(len(lst)):
    regex = lst[i]
    temp = regex.strip('\n')
    if i == len(lst) - 1: rCAVIEWER += f"({temp})"
    else: rCAVIEWER += f"({temp})|"
rCAVIEWER = re.compile(rCAVIEWER)

# rCAVIEWER = re.compile(
#   r'''(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(([BSbs][0-8]*/?[BSbs][0-8]*|[BSbs]?[0-8]*/[BSbs]?[0-8]*)History)'''
#   r'''|(([BSbs][0-4]*/?[BSbs][0-4]*?|[BSbs]?[0-4]*/[BSbs]?[0-4]*)VHistory)'''
#   r'''|(([BSbs][0-6]*/?[BSbs][0-6]*|[BSbs]?[0-6]*/[BSbs]?[0-6]*)HHistory)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?History)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#]History)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?History)'''
#   r'''|(([BSbs][0-8]*/?[BSbs][0-8]*|[BSbs]?[0-8]*/[BSbs]?[0-8]*)Symbiosis)'''
#   r'''|(([BSbs][0-4]*/?[BSbs][0-4]*?|[BSbs]?[0-4]*/[BSbs]?[0-4]*)VSymbiosis)'''
#   r'''|(([BSbs][0-6]*/?[BSbs][0-6]*|[BSbs]?[0-6]*/[BSbs]?[0-6]*)HSymbiosis)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?Symbiosis)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#]Symbiosis)'''
#   r'''|(R[0-9]+,C[0|2],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?Symbiosis)'''
#   r'''|(R[0-9]+,C[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,C[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,C[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(R[0-9]+,C[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?,[A-Fa-f0-9]+)'''
#   r'''|(R[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,G(0[-])?[1-9][0-9]*([-][1-9][0-9]*)*,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,G(0[-])?[1-9][0-9]*([-][1-9][0-9]*)*,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,G(0[-])?[1-9][0-9]*([-][1-9][0-9]*)*,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(R[0-9]+,G[0-9]+,L[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RB(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RS(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,G[0-9]+,L[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RB(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RS(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,G[0-9]+,L[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RB(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RS(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(R[0-9]+,G[0-9]+,L[0-9]+,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RB(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,RS(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?,[A-Fa-f0-9]+)'''
#   r'''|(R[0-9]+,I[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,I[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,I[0-9]+,S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(R[0-9]+,D[0|1],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N@([A-Fa-f0-9]+)?[HL]?)'''
#   r'''|(R[0-9]+,D[0|1],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,N[ABbCGHLMNX23*+#])'''
#   r'''|(R[0-9]+,D[0|1],S(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,B(((\d,(?=\d))|(\d-(?=\d))|\d)+)?,NW[A-Fa-f0-9]+[HL]?)'''
#   r'''|(B((0|1-[a]+|1[a]*|2-[acehij]+|2[acehij]*|3-[acehijn]+|3[acehijn]*|4-[acehijnopqrtuv]+|4[acehijnopqrtuv]*|5-[acehijn]+|5[acehijn]*|6-[acehij]+|6[acehij]*|7-[a]+|7[a]*|8))*/S((0|1-[a]+|1[a]*|2-[acehij]+|2[acehij]*|3-[acehijn]+|3[acehijn]*|4-[acehijnopqrtuv]+|4[acehijnopqrtuv]*|5-[acehijn]+|5[acehijn]*|6-[acehij]+|6[acehij]*|7-[a]+|7[a]*|8))*(/NK)?)'''
#   r'''|(B((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*/S((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*(/NM)?)'''
#   r'''|(B((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*/S((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*(/NFC)?)'''
#   r'''|(B((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*/S((0|1-[ce]+|1[ce]*|2-[aceikn]+|2[aceikn]*|3-[aqrceiyjkn]+|3[aqrceiyjkn]*|4-[aceijknqrtwyz]+|4[aceijknqrtwyz]*|5-[aqrceiyjkn]+|5[aqrceiyjkn]*|6-[aceikn]+|6[aceikn]*|7-[ce]+|7[ce]*|8))*(/NFE)?)'''
#   r'''|(B((0|1-[ac]+|1[ac]*|2-[acehijn]+|2[acehijn]*|3-[pacehijno]+|3[pacehijno]*|4-[acehijnopqrtuvw]+|4[acehijnopqrtuvw]*|5-[pacehijno]+|5[pacehijno]*|6-[acehijn]+|6[acehijn]*|7-[ac]+|7[ac]*|8))*/S((0|1-[ac]+|1[ac]*|2-[acehijn]+|2[acehijn]*|3-[pacehijno]+|3[pacehijno]*|4-[acehijnopqrtuvw]+|4[acehijnopqrtuvw]*|5-[pacehijno]+|5[pacehijno]*|6-[acehijn]+|6[acehijn]*|7-[ac]+|7[ac]*|8))*(/NC2)?)'''
#   r'''|(W[0-9]+)'''
#   r'''|(R[1-9][0-9]*,C[2-9][0-9]*,W[0-9]+)'''
# )

# matches multiline XRLE; currently cannot, however, match headerless patterns (my attempts thus far have forced re to take way too many steps)
# does not match rules with >24 states
rXRLE = re.compile(
    r'x ?= ?\d+, ?y ?= ?\d+(?:, ?rule ?= ?([^ \n]+))?\n([\d.A-Z]*[.A-Z$][\d.A-Z$\n]*!?|[\dob$]*[ob$][\dob$\n]*!?)',
    re.I)

# splits RLE into its runs
rRUNS = re.compile(r'([0-9]*)([a-z][A-Z]|[ob.A-Z])')
# [rRUNS.sub(lambda m: '10'[m[2] == 'b'] * int(m[1] or 1), pattern) for pattern in patlist[i]]

# unrolls $ signs
rDOLLARS = re.compile(r'(\d+)\$')


# ---- #


class Trackbox:
    def __init__(self, n_gens, r, distance, x0, y0, dx, dy):
        self.n_gens = n_gens
        self.dist = distance
        self.r, self.r_calc = r, r / ROOT_2
        self.x0, self.y0 = x0, y0
        self.dx, self.dy = dx, dy

    @classmethod
    def from_lists(cls, positions, bboxes):
        n_gens = len(positions)
        dx, dy = positions[-1]
        m = dy / dx
        b = -m * positions[0][0]

        def x_prime(x, y):
            return x * dx / d + (y - b) * dy / d

        def y_prime(x, y):
            return (y - b) * dx / d - x * dy / d

        d = (dx ** 2 + dy ** 2) ** 0.5  # dx and dy double as "x2" and "y2" in distance formula
        r = max(
            abs(min(x_prime(*pos) - d * (gen / n_gens) for gen, pos in enumerate(positions))),
            max(x_prime(*pos) - d * (gen / n_gens) for gen, pos in enumerate(positions)),
            abs(min(starmap(y_prime, positions))),
            max(starmap(y_prime, positions))
        )
        return cls(n_gens, r, d, dx, dy)

    def __call__(self, gen):
        t = gen / self.n_gens
        return (
            t * self.dx - self.r_calc,
            t * self.dx + self.r_calc,
            t * self.dy - self.r_calc,
            t * self.dy + self.r_calc
        )


def _replace(m):
    return '$' * int(m[1])


def parse(lines, current):
    patlist = [x.strip("\n") for x in lines if re.match("\\S+", x)]

    os.remove(f'{current}_out.rle')
    # `positions` needs to be a list, not a generator
    # because it's returned from this function, so
    # it gets pickled by run_in_executor -- and
    # generators can't be pickled
    # [(0, 0), (-1, 1), (0, 0), (-1, -1), (1, -2), (0, -1), (2, -2), (1, -1), (0, -2), (-1, 1)]
    positions = list(map(lambda x: eval(x) if x != '-2147483648,-2147483648' else (0, 0), patlist[::3]))
    # [(5, 3), (7, 1), (5, 3), (7, 5), (3, 7), (5, 5), (1, 7), (3, 5), (5, 7), (7, 1)]
    bboxes = list(map(eval, patlist[1::3]))

    # trackbox = Trackbox.from_lists(positions, bboxes)

    # Determine the bounding box to make gifs from
    # The rectangle: xmin <= x <= xmax, ymin <= y <= ymax
    # where (x|y)(min|max) is the min/max coordinate across all gens.
    xmins, ymins = zip(*positions)
    (widths, heights), maxwidth, maxheight = zip(*bboxes), max(w for w, h in bboxes), max(h for w, h in bboxes)
    xmaxes = starmap(operator.add, zip(xmins, widths))
    ymaxes = starmap(operator.add, zip(ymins, heights))
    xmin, ymin, xmax, ymax = min(xmins), min(ymins), max(xmaxes), max(ymaxes)
    # Bounding box: top-left x and y, width and height
    bbox = xmin, ymin, xmax - xmin, ymax - ymin

    # ['4b3$o', '3o2b'] -> ['4b$$$o', '3o2b']
    # ['4b$$$o', '3o2b'] -> [['4b', '', '', '', 'o'], ['3o2b']]
    return [i.replace('!', '').split('$') for i in
            (rDOLLARS.sub(_replace, j) for j in patlist[2::3])], positions, bbox, (maxwidth, maxheight)


def makeframes(current, gen, step, patlist, positions, bbox, pad, colors, bg, track, trackmaxes, grid):
    xmin, ymin, width, height = bbox
    if track:
        width, height = trackmaxes
    duration = min(1 / 6, max(1 / 60, 5 / gen / step) if gen else 1)
    with imageio.get_writer(f'{current}.gif', mode='I', duration=str(duration)) as gif_writer:
        for pat, (xpos, ypos) in zip(patlist, positions):
            dx, dy = (1, 1) if track else (1 + (xpos - xmin), 1 + (ypos - ymin))
            frame = [[bg] * (2 + width) for _ in range(2 + height)]

            # Draw the pattern onto the frame by replacing segments of background rows
            for i, flat_row in enumerate(
                    [
                        bg if char in '.b' else colors[char]
                        for run, char in rRUNS.findall(row)
                        for _ in range(int(run or 1))
                    ]
                    for row in pat
            ):
                frame[dy + i][dx:dx + len(flat_row)] = flat_row
            anchor = min(height, width)
            mul = -(-100 // anchor) if anchor <= 100 else 1
            first_grid = 0 if grid else None
            gif_writer.append_data(
                np.asarray(
                    mutils.scale(
                        (mutils.scale(row, mul, grid=first_grid) for row in frame),
                        mul, grid=(0, 0, 0) if grid else None
                    ),
                    np.uint8
                ))
            if os.stat(f'{current}.gif').st_size > 7500000:
                return True
    return False


def genconvert(gen: int):
    if int(gen) > 0:
        return int(gen) - 1
    raise ValueError  # bad gen (less than or equal to zero)


class CA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.BOTS_N_MUTE = self.bot.get_channel(BOTS_N_MUTE)
        self.dir = os.path.dirname(os.path.abspath(__file__))
        self.ppe = ProcessPoolExecutor()
        self.tpe = ThreadPoolExecutor()  # or just None
        self.loop = bot.loop
        self.simlog = deque(maxlen=5)
        self.defaults = (*[[self.ppe, 'ProcessPoolExecutor']] * 2, [self.tpe, 'ThreadPoolExecutor'])
        self.opts = {'tpe': [self.tpe, 'ThreadPoolExecutor'], 'ppe': [self.ppe, 'ProcessPoolExecutor']}
        self.rulecache = None
        self.gencache = None

    @staticmethod
    def state_from(val, n_states):
        if n_states < 3:
            return 'bo'[val] if isinstance(val, int) else int(val == 'o')
        return mutils.state_from(val)

    def get_rand_state(self, n_states: int, last_state: str, allowed_states: {int}) -> str:
        if last_state is None:
            return self.state_from(random.randrange(0, n_states), n_states)
        new = last_state = self.state_from(last_state, n_states)
        while new == last_state or new not in allowed_states:
            new = random.randrange(0, n_states)
        return self.state_from(new, n_states)

    def makesoup(self, rulestring: str, n_states: int, x: int, y: int, allowed_states: {int}) -> str:
        """Generates random soup as RLE with specified dimensions"""
        rle = f'x = {x}, y = {y}, rule = {rulestring}\n'
        last_state = None
        for row in range(y):
            pos = x
            while pos > 0:
                # below could also just be random.randint(1,x) but something likes this gives natural-ish-looking results
                runlength = math.ceil(-math.log(1 - random.random()))
                if runlength > pos:
                    runlength = pos  # or just `break`, no big difference qualitatively
                last_state = self.get_rand_state(n_states, last_state, allowed_states)
                rle += (str(runlength) if runlength > 1 else '') + last_state
                pos -= runlength
            rle += '$\n' if y > row + 1 else '!\n'
        return rle

    @staticmethod
    def _extend(n, *, thresh=50):
        """From BlinkerSpawn"""
        if n <= thresh:
            return 2 * n
        quotient = n // next(i for i in count(math.ceil(n / thresh)) if not n % i)
        return n + quotient * (thresh // quotient)

    def cancellation_check(self, ctx, orig_msg, rxn, usr):
        if rxn.message.id != orig_msg.id:
            return False
        correct_emoji = rxn.emoji == '\N{WASTEBASKET}'
        if usr != ctx.message.author:
            return correct_emoji and (rxn.count > 3 or usr.id == WRIGHT)
        return correct_emoji

    async def do_gif(self, execs, current, gen, step, colors, track, bg, grid):
        # Getting colors
        lines = []
        in_colors = False
        with open(f"{current}_out.rle", "r") as file:
            for line in file.readlines():
                line = line.rstrip('\n')
                if "@COLOR" in line:
                    in_colors = True
                    continue
                if in_colors:
                    # '0    255 255 255   random comments' ->
                    # {0: (255, 255, 255)}
                    state, rgb = line.split(None, 1)

                    if state == 0:
                        colors['.'] = tuple(map(int, rgb.split()[:3]))
                        colors['b'] = tuple(map(int, rgb.split()[:3]))
                    elif state == 1:
                        colors['A'] = tuple(map(int, rgb.split()[:3]))
                        colors['o'] = tuple(map(int, rgb.split()[:3]))
                    else:
                        colors[chr(int(state) + 64)] = tuple(map(int, rgb.split()[:3]))
                else:
                    lines.append(line)

        start = time.perf_counter()
        patlist, positions, bbox, trackmaxes = await self.loop.run_in_executor(
            execs[0][0], parse,
            lines, current
        )
        end_parse = time.perf_counter()
        oversized = await self.loop.run_in_executor(
            execs[1][0], makeframes,
            current, gen, step, patlist, positions, bbox,
            len(str(gen)), colors, bg, track, trackmaxes,
            grid
        )
        end_makeframes = time.perf_counter()
        return start, end_parse, end_makeframes, oversized

    async def run_bgolly(self, current, algo, gen, step, rule):
        # max_mem = int(os.popen('free -m').read().split()[7]) // 1.25 TODO: use
        timeout = 5 * 60
        preface = f'{self.dir}/resources/bgolly'
        if '::' in rule:
            rule = f"{rule}_{current.split('/')[-1]}"
        algo = algo.split('::')[0]
        ruleflag = f's {self.dir}/' if algo == 'RuleLoader' else f'r {rule}'
        if algo == "CAViewer":
            preface = f'{self.dir}/resources/bin/CAViewer'

            p = subprocess.Popen(f"timeout {timeout} {preface} sim -g {gen} -s {step} -i {current}_in.rle -o {current}_out.rle".split(),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out = p.communicate()

            return out[1].decode("utf-8")
        else:
            return os.popen(
                f'timeout {timeout} {preface} -a "{algo}" -{ruleflag} -m {gen} -i {step} -o {current}_out.rle {current}_in.rle').read()

    def moreinfo(self, ctx):
        return f"'{ctx.prefix}help sim' for more info"

    async def write_rule_from_generator(self, gen_name, rulestring, fp):
        module = types.ModuleType('<custom>')
        await self.loop.run_in_executor(None,
                                        exec,
                                        await self.loop.run_in_executor(None,
                                                                        marshal.loads,
                                                                        await self.bot.pool.fetchval(
                                                                            '''SELECT module FROM algos WHERE name = $1::text''',
                                                                            gen_name)
                                                                        ),
                                        module.__dict__
                                        )
        try:
            rulestring = await self.loop.run_in_executor(None, module.rulestring, rulestring)
        except AttributeError:
            pass  # no need to modify rulestring then
        fp.write(await self.loop.run_in_executor(None, module.main, rulestring))
        return rulestring

    @mutils.group('Simulate an RLE and output to GIF', args=True)
    async def sim(
            self, ctx,
            *,
            gen: (r'^\d+$', int) = None,
            pat: r'[\dob$]*[ob$][\dob$\n]*!?' = '',
            step: (r'^\d+$', int) = None,
            rule: r'(?:::)?[^-\s:][^\s:]*' = '',  # no flags, so no hyphen at start
            flags,
            **kwargs
    ):
        """
        # Simulates PAT with output to animated gif. #
        <[ARGS]>
        GEN: Generation to simulate up to.
        STEP: Step size. Affects simulation speed. If omitted, defaults to 1.
        RULE: Rulestring to simulate PAT under. If omitted, defaults to B3/S23 or rule specified in PAT.
        PAT: One-line rle or .lif file to simulate. If omitted, uses last-sent Golly-compatible pattern (which should be enclosed in a code block and therefore can be a multiliner).
        #TODO: streamline GIF generation process, implement proper LZW compression, implement flags & gfycat upload

        <[FLAGS]>
        -ca: Use CAViewer instead of the default bgolly.
        -h: Use HashLife instead of the default QuickLife.
        -time: Include time taken to create gif (in seconds w/hundredths) alongside GIF.
          all: Provide verbose output, showing time taken for each step alongside the type of executor used.
        -tag: When finished, tag requester. Useful for time-intensive simulations.
        -id: Has no function besides appearing above the final output, but can be used to tell apart simultaneously-created gifs.
        -t: Track. Rudimentary impl, nothing smooth -- goes by generation.
        -g: Show grid lines.
        """
        given_rule, display_given_rule = rule, False
        rand = kwargs.get('rand')
        dims = kwargs.get('soup_dims')
        colors = {}
        if 'execs' in flags:
            flags['execs'] = flags['execs'].split(',')
            execs = [self.opts.get(v, self.defaults[i]) for i, v in enumerate(flags['execs'])]
        else:
            execs = self.defaults

        if '-h' in flags:
            algo = 'HashLife'
        elif '-ca' in flags:
            algo = 'CAViewer'
        else:
            algo = 'QuickLife'

        track = 'track' in flags or 't' in flags
        grid = 'grid' in flags or 'g' in flags

        person_to_tag = ""

        try:
            step, gen = (1, gen) if step is None else sorted((step, gen))
        except ValueError:
            return await ctx.send(f"`Error: No GEN given. {self.moreinfo(ctx)}`")
        gen = genconvert(gen)
        if gen / step > 2500:
            return await ctx.send(f"`Error: Cannot simulate more than 2500 frames. {self.moreinfo(ctx)}`")
        if not pat and not rand:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rXRLE.search(msg.content)
                if rmatch:
                    person_to_tag = msg.author
                    pat = rmatch.group(2)
                    if rmatch.group(1):
                        rule = rmatch.group(1)
                    break
            if not pat:
                return await ctx.send(f"`Error: No PAT given and none found in last 50 messages. {self.moreinfo(ctx)}`")
        elif pat and not rand:
            pat = pat.strip('`')

        if not rule:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rLtL.search(msg.content) or rRULESTRING.search(msg.content)
                if rmatch:
                    rule = rmatch.group()
                    break
            else:
                rule = ''

        bg, fg = ((255, 255, 255), (0, 0, 0)) if 'bw' in flags else ((54, 57, 62), (255, 255, 255))
        colors = {'o': fg, 'b': bg}

        current = f'{self.dir}/{ctx.message.id}'
        rule = ''.join(rule.split()) or 'B3/S23'

        n_states = 2
        if '::' in given_rule:
            rulestring, name = given_rule.split('::')
            rulestring = rulestring or rule.split('::')[0]
            algo = f'RuleLoader::{name}'
            with open(f'{self.dir}/{rulestring}_{ctx.message.id}.rule', 'w+') as ruleout:
                rulestring = await self.write_rule_from_generator(name, rulestring, ruleout)
                _, n_states, colors = mutils.extract_rule_info(ruleout, False)
                bg, colors = mutils.colorpatch(colors, n_states, fg, bg)
            rule = f'{rulestring}_{ctx.message.id}'
            given_rule = rulestring
            display_given_rule = True
        elif rLtL.match(rule):
            algo = 'Larger than Life'
            n_states = 2 + int(rLtL.match(rule)[1])
        elif not rRULESTRING.fullmatch(rule) and rCAVIEWER.fullmatch(rule):
            algo = 'CAViewer'
        elif not rRULESTRING.fullmatch(rule) and algo != "CAViewer":
            algo = 'RuleLoader'

        if algo == 'RuleLoader':
            try:
                rulename, rulefile, n_states, colors = await self.bot.pool.fetchrow('''
                  SELECT name, file, n_states, colors FROM rules WHERE name = $1::text
                ''', rule)
            except ValueError:  # not enough values to unpack
                return await ctx.send('`Error: Rule not found`')
            bg, colors = mutils.colorpatch(json.loads(colors), n_states, fg, bg)
            with open(f'{self.dir}/{rulename}_{ctx.message.id}.rule', 'wb') as ruleout:
                ruleout.write(rulefile)
        if algo == 'Larger than Life':
            n_states = int(rule.split('C')[1].split(',')[0])
            if n_states > 2:
                colors = mutils.ColorRange(n_states, (255, 255, 0), (255, 0, 0)).to_dict()
        if rule.count('/') > 1 and '::' not in rule and algo != "CAViewer":
            algo = 'Generations'
            n_states = int(rule.split('/')[-1])
            colors = mutils.ColorRange(n_states).to_dict()

        if rand:
            rule_ = rule.split('::')[0]
            if algo == 'RuleLoader':
                rule_ += f'_{ctx.message.id}'
            include, exclude = kwargs['soup_include_states'], kwargs['soup_exclude_states']
            allowed_states = include if include else set(range(n_states))
            if exclude:
                allowed_states -= exclude
            if len(allowed_states) < 2:
                return await ctx.send('`Error: random soup cannot be generated with fewer than 2 states allowed`')
            pat = await self.loop.run_in_executor(
                None, self.makesoup,
                rule_, n_states, *dims, allowed_states
            )
            dims = f'{dims[0]}\u00d7{dims[1]}'

        details = (
                (f'Running `{dims}` soup' if rand else f'Running supplied pattern')
                + f' in rule `{given_rule if display_given_rule else rule}` with '
                + f'step `{step}` for `{1 + gen}` generation(s)'
                + (f' using `{algo}`.' if algo != 'QuickLife' else '.')
        )
        announcement = await ctx.send(details)
        curlog = Log(ctx.author.mention, rule, ctx.message.created_at, Status.WAITING)
        self.simlog.append(curlog)
        writrule = f'{rule}_{ctx.message.id}' if algo == 'RuleLoader' else rule
        with open(f'{current}_in.rle', 'w') as infile:
            infile.write(pat if pat.startswith('x = ') else f'x = 0, y = 0, rule = {writrule}\n{pat}')
        bg_err = await self.run_bgolly(current, algo, gen, step, rule)
        if bg_err:
            curlog.status = Status.FAILED
            return await ctx.send(f'```{bg_err}```')
        await announcement.add_reaction('\N{WASTEBASKET}')
        curlog.status = Status.SIMMING

        try:
            resp = await mutils.await_event_or_coro(
                self.bot,
                event='reaction_add',
                coro=self.do_gif(execs, current, gen, step, colors, track, bg, grid),
                ret_check=lambda obj: isinstance(obj, discord.Message),
                event_check=lambda rxn, usr: self.cancellation_check(ctx, announcement, rxn, usr)
            )
        except FileNotFoundError:
            curlog.status = Status.FAILED
            return await ctx.send(f'Error: Timed out')
        except concurrent.futures.process.BrokenProcessPool:
            curlog.status = Status.FAILED
            return await ctx.send("Error: You almost made me crash... :angry:")
        except MemoryError:
            curlog.status = Status.FAILED
            return await ctx.send("Error: You made me run out of memory... :angry:")
        except Exception as e:
            curlog.status = Status.FAILED
            return await ctx.send(f"Error: `{str(e)}`")
        try:
            start, end_parse, end_makeframes, oversized = resp['coro']
        except (KeyError, ValueError):
            curlog.status = Status.CANCELED
            return await resp['event'][0].message.delete()
        content = (
                (ctx.message.author.mention if 'tag' in flags else '')
                + (f' **{discord.utils.escape_mentions(flags["id"])}** \n' if 'id' in flags else '')
                + '{time}'
        )
        curlog.status = Status.COMPLETED

        try:
            gif = await ctx.send(
                content.format(
                    time=str(
                        {
                            'Times': '',
                            '**Parsing frames**': f'{round(end_parse - start, 2)}s ({execs[0][1]})',
                            '**Saving frames to GIF**': f'{round(end_makeframes - end_parse, 2)}s ({execs[1][1]})',
                            '(**Total**': f'{round(end_makeframes - start, 2)}s)'
                        }
                    ).replace("'", '').replace(',', '\n').replace('{', '\n').replace('}', '\n')
                    if flags.get('time') == 'all'
                    else f'{round(end_makeframes - start, 2)}s'
                    if 'time' in flags
                    else ''
                ) + ('\n(Truncated to fit under 8MB)' if oversized else ''),
                file=discord.File(f'{current}.gif')
            )
            newline = '\n' * bool(gif.content)
            if 'tag' not in flags:
                if person_to_tag != "":
                    await gif.edit(content=f'By {person_to_tag.mention}{newline}{gif.content}')
                else:
                    await gif.edit(content=f'By {ctx.message.author.mention}{newline}{gif.content}')
        except discord.errors.HTTPException as e:
            curlog.status = Status.FAILED
            return await ctx.send(
                f'{ctx.message.author.mention}\n`HTTP 413: GIF too large. Try a higher STEP or lower GEN!`')

        def extension_or_deletion_check(rxn, usr):
            if usr == ctx.message.author or usr.id == WRIGHT:
                if rxn.emoji in '➕⏩' and rxn.message.id == gif.id:
                    return True
                return rxn.emoji == '\N{WASTEBASKET}' and rxn.message.id == announcement.id

        try:
            while True:
                if gen < 2500 * step and not oversized:
                    await gif.add_reaction('➕')
                await gif.add_reaction('⏩')
                rxn, _ = await self.bot.wait_for('reaction_add', timeout=25.0, check=extension_or_deletion_check)
                await gif.delete()
                if rxn.emoji == '\N{WASTEBASKET}':
                    await announcement.delete()
                    break
                if rxn.emoji == '➕':
                    gen = self._extend(gen)
                else:
                    step *= 2
                    oversized = False
                details = (
                        (f'Running `{dims}` soup' if rand else f'Running supplied pattern')
                        + f' in rule `{rule}` with step `{step}` for `{gen + bool(rand)}` generation(s)'
                        + (f' using `{algo}`.' if algo != 'QuickLife' else '.')
                )
                await announcement.edit(content=details)
                bg_err = await self.run_bgolly(current, algo, gen, step, rule)
                if bg_err:
                    return await ctx.send(f'`{bg_err}`')
                resp = await mutils.await_event_or_coro(
                    self.bot,
                    event='reaction_add',
                    coro=self.do_gif(execs, current, gen, step, colors, track, bg, grid),
                    ret_check=lambda obj: isinstance(obj, discord.Message),
                    event_check=lambda rxn, usr: self.cancellation_check(ctx, announcement, rxn, usr)
                )
                try:
                    start, end_parse, end_makeframes, oversized = resp['coro']
                except KeyError:
                    return await resp['event'][0].message.delete()
                try:
                    gif = await ctx.send(
                        content.format(
                            time=str(
                                {
                                    'Times': '',
                                    '**Parsing frames**': f'{round(end_parse - start, 2)}s ({execs[0][1]})',
                                    '**Saving frames to GIF**': f'{round(end_makeframes - end_parse, 2)}s ({execs[1][1]})',
                                    '(**Total**': f'{round(end_makeframes - start, 2)}s)'
                                }
                            ).replace("'", '').replace(',', '\n').replace('{', '\n').replace('}', '\n')
                            if flags.get('time') == 'all'
                            else f'{round(end_makeframes - start, 2)}s'
                            if 'time' in flags
                            else ''
                        ) + ('\n(Truncated to fit under 8MB)' if oversized else ''),
                        file=discord.File(f'{current}.gif')
                    )
                    if 'tag' not in flags:
                        await gif.edit(content=f'By {ctx.author.mention}{newline}{gif.content}')
                except discord.errors.HTTPException as e:
                    return await ctx.send(f'`HTTP 413: GIF too large. Try a higher STEP or lower GEN!`')
        except asyncio.TimeoutError:
            # trigger the finally block
            pass
        finally:
            gif = await ctx.channel.fetch_message(gif.id)  # refresh reactions
            await announcement.remove_reaction('\N{WASTEBASKET}', ctx.guild.me)
            [await gif.remove_reaction(rxn, ctx.guild.me) for rxn in gif.reactions]
            os.remove(f'{current}.gif')
            os.remove(f'{current}_in.rle')
            if algo == 'RuleLoader':
                os.remove(f'{self.dir}/{rule}_{ctx.message.id}.rule')

    @sim.error
    async def sim_error(self, ctx, error):
        # Missing GEN:
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f'`Error: No {error.param.name.upper()} given. {self.moreinfo(ctx)}`')
        # Bad argument:
        if isinstance(error, (
                commands.BadArgument, ZeroDivisionError)):  # BadArgument on failure to convert to int, ZDE on gen=0
            if '"' in str(error):
                badarg = str(error).split('"')[3].split('"')[0]
                return await ctx.send(f'`Error: Invalid {badarg.upper()}. {self.moreinfo(ctx)}`')
            return await ctx.send(f'`Error: {error}.`')
        raise error

    @sim.command(args=True)
    async def rand(
            self, ctx,
            *,
            dims: r'^\d+x\d+$' = '16x16',
            gen: (r'^\d+$', int) = None,
            step: (r'^\d+$', int) = None,
            rule: r'(?:::)?[^-\s:][^\s:]*' = None,
            flags
    ):
        """
        # Simulates a random soup in given rule with output to GIF. Dims default to 16x16. #
        # If either flag is given but empty (e.g. `-include` rather than `-include:1,2,3..5`), it will count as not having been given. #
        # -include and -exclude cannot be given at the same time. If they are, only -include will be counted. #
        # Lastly, if the use of either flag results in less than 2 states' being allowed, an error will be returned. #
        
        <[ARGS]>
        DIMS: "AxB" (sans quotes), where A and B are the desired soup's width and height separated by the literal character "x".
        {inherits}
        
        <[FLAGS]>
        -include: States to include, delimited by commas. Additionally, nutshell-style range notation is accepted.
        -exclude: Alternatively, states to exclude. Ditto above.
        {inherits}
        """
        nums = gen, step
        try:
            step, gen = sorted(nums)
        except TypeError:
            step, gen = 1, gen or step
            if gen is None:
                return await ctx.send(f'`Error: No GEN given. {self.moreinfo(ctx)}`')
        if not rule:
            async for msg in ctx.channel.history(limit=50):
                rmatch = rLtL.search(msg.content) or rRULESTRING.search(msg.content)
                if rmatch:
                    rule = rmatch.group()
                    break
        x, y = map(int, dims.split('x'))
        if x > 1500 or y > 1500:
            return await ctx.send(
                f'`Error: Cannot simulate soup with dimension greater than 1500. {self.moreinfo(ctx)}`')
        include, exclude = set(), set()
        if 'include' in flags:
            include = mutils.flatten_range_list(flags.pop('include').split(','))
        elif 'exclude' in flags:
            exclude = mutils.flatten_range_list(flags.pop('exclude').split(','))
        await ctx.invoke(
            self.sim,
            gen=int(gen),
            step=int(step),
            rule=rule or 'B3/S23',
            flags=flags,
            rand=True,
            soup_dims=(x, y),
            soup_include_states=include,
            soup_exclude_states=exclude
        )

    @sim.command('Gives a log of recent sim invocations')
    async def log(self, ctx):
        entries = []
        comp = ('⌛', '💬', '🗑', '✅', '❌')
        for log in self.simlog:
            entries.append(
                f'• {log.invoker}'
                f' in `{log.rule}`'
                f" at `{log.time.strftime('%H:%M')}`:"
                f' {comp[log.status.value]} {log.status.name.title()}'
            )
        await ctx.send(embed=discord.Embed(title='Last 5 sims', description='\n'.join(entries)))

    @mutils.command('Show uploaded rules')
    async def rules(self, ctx, rule=None):
        """
        # If no argument is passed, displays all rules (paginated by tens). #
        <[ARGS]>
        RULE: Rulename. If a rule by this name (case-sensitive) has been uploaded, displays that rule's info and gives its rulefile.
        [or]
        MEMBER: If the member mentioned is present in the server, shows rules uploaded by them.
        """
        if self.rulecache is None:
            self.rulecache = [
                {'name': i['name'], 'blurb': i['blurb'], 'file': i['file'], 'uploader': i['uploader']}
                for i in
                await self.bot.pool.fetch(f'''SELECT DISTINCT ON (name) name, uploader, file, blurb FROM rules''')
            ]
        if rule is None:
            offset = 0
            say, msg = ctx.send, None
            while True:
                msg = await say(embed=discord.Embed(
                    title='Rules',
                    description='\n'.join(
                        f"• {i['name']} ({get_member_bismuth(ctx.guild, i['uploader'])}): {i['blurb']}"
                        for i in islice(self.rulecache, offset, offset + 10)
                    )
                )) or msg
                say = msg.edit
                left, right = await mutils.get_page(ctx, msg)
                if left:
                    offset = max(0, offset - 10)
                elif right:
                    offset += offset + 10 < len(self.rulecache) and 10
        try:
            member = await commands.MemberConverter().convert(ctx, rule)
        except commands.BadArgument:
            rule = next(d for d in self.rulecache if d['name'] == rule)
            with io.BytesIO(rule['file']) as b:
                b.seek(0)
                return await ctx.send(embed=discord.Embed(
                    title=rule['name'],
                    description=f"Uploader: {self.bot.get_user(rule['uploader'])}\nBlurb: {rule['blurb']}"
                ),
                    file=discord.File(b, rule['name'] + '.rule')
                )
        else:
            return await ctx.send(embed=discord.Embed(
                title=f'Rules by {member}',
                description='\n'.join(
                    f"• {d['name']}: {d['blurb']}"
                    for d in self.rulecache
                    if d['uploader'] == member.id
                )
            ))

    async def _insert_rule(self, *args):
        query = '''
        INSERT INTO rules (
          uploader, blurb, file, name, n_states, colors
        )
        SELECT $1::bigint, $2::text, $3::bytea, $4::text, $5::int, $6::text
            ON CONFLICT (name)
            DO UPDATE
           SET uploader=$1::bigint, blurb=$2::text, file=$3::bytea, name=$4::text, n_states=$5::int, colors=$6::text
        '''
        await self.bot.pool.execute(query, *args)
        self.rulecache = None

    async def _insert_generator(self, *args):
        await self.bot.pool.execute('''
          INSERT INTO algos (
              name, uploader, plaintext, module, blurb
          )
          SELECT $1::text, $2::bigint, $3::bytea, $4::bytea, $5::text
              ON CONFLICT (name)
              DO UPDATE
              SET uploader=$2::bigint, plaintext=$3::bytea, module=$4::bytea, blurb=COALESCE(algos.blurb, $5::text)
          ''',
                                    *args
                                    )

    @mutils.command('Upload an asset (just ruletables for now)')
    async def upload(self, ctx, *, blurb=''):
        """
        # Attach a ruletable file to this command to have it reviewed by Conwaylife Lounge moderators. #
        # If acceptable, it will be added to Caterer and be usable in !sim. #
        <[ARGS]>
        BLURB: Short description of this rule. Min 10 characters, max 90.
        """
        if len(blurb) < 10:
            return await ctx.send('Please provide a short justification/explanation of this rule!')
        if len(blurb) > 90:
            return await ctx.send('Please shorten your description. Max 90 characters.')
        attachment = ctx.message.attachments[0]
        file = await attachment.to_file()
        approved, should_ping = await self.bot.approve_asset(file, blurb, ctx.author, 'rule')
        if approved:
            await self._insert_rule(ctx.author.id, blurb, await attachment.read(), *mutils.extract_rule_info(file.fp))
            self.rulecache = None
            await ctx.thumbsup(ctx.author, f'Rule `{attachment.filename}` was approved!', should_ping)
        await ctx.thumbsdown(ctx.author, f'Rule `{attachment.filename}` was rejected or not parsable.', override=False)

    async def _reapprove(self, ctx, created_at, file, name, blurb, author, kind):
        approved, should_ping = await self.bot.approve_asset(file, blurb, author, kind, created_at=created_at,
                                                             name=name)
        if approved:
            content = file.fp.read()
            file.reset()
            if kind == 'rule':
                await self._insert_rule(ctx.author.id, blurb, content, *mutils.extract_rule_info(file.fp))
            elif kind == 'generator':
                await self._insert_generator(
                    name, ctx.author.id, content,
                    await self.loop.run_in_executor(
                        None,
                        marshal.dumps,
                        await self.loop.run_in_executor(None, compile, content, '<custom>', 'exec', 0, False, 2)
                    ),
                    blurb
                )
            await ctx.thumbsup(author, f'{kind.upper()} `{name}` was accepted!', channel=self.BOTS_N_MUTE)
        await ctx.thumbsdown(author, f'{kind.upper()} `{name}` was rejected or not parsable.', override=False,
                             channel=self.BOTS_N_MUTE)

    @mutils.command()
    async def reup(self, ctx):
        if ctx.channel.id != ASSETS:
            return await ctx.thumbsdown()
        coros = []
        async for msg in ctx.channel.history().filter(lambda msg: msg.author == self.bot.user):
            pre, blurb = msg.content.split('\n', 1)[0].split(':', 1)
            kind, name = pre.split(' ')
            coros.append(self._reapprove(
                ctx,
                msg.created_at,
                # technically still works (only a minor delay btwn user invoking !upload/!register and btwn caterer posting this msg)
                await msg.attachments[0].to_file(),
                name,
                blurb,
                msg.mentions[-1],
                kind
            ))
            await msg.delete()
        await ctx.thumbsup()
        await asyncio.wait(coros)

    @mutils.command()
    async def delrule(self, ctx, name):
        and_condition = ''
        if not await self.bot.is_owner(ctx.author):
            and_condition = 'AND uploader = $2::bigint'
        try:
            if name.startswith('user:'):
                status = await self.bot.pool.execute(
                    f'''DELETE FROM rules WHERE uploader = $1::bigint {and_condition}''',
                    *(
                         (await commands.MemberConverter().convert(ctx, name[1 + name.index(':'):])).id,
                         ctx.author.id
                     )[:1 + bool(and_condition)]
                )
            else:
                status = await self.bot.pool.execute(
                    f'''DELETE FROM rules WHERE name = $1::text {and_condition}''',
                    *(name, ctx.author.id)[:1 + bool(and_condition)]
                )
        except:
            await ctx.thumbsdown()
            raise
        if int(status.split()[-1]) == 0:
            return await ctx.thumbsdown()
        self.rulecache = None
        await ctx.thumbsup()

    @mutils.command('Register a custom rulefile-generating python script')
    async def register(self, ctx, name, *, blurb):
        """
        # Register a custom rulefile-generating python module. #
        # Must be compatible with Python 3.6, and additionally must #
        # contain a "main()" function that can be called with a single #
        # rulestring argument (the user's input) to produce a rulefile. #
        #
        # Due to bad-design-related limitations, your rulestrings must be filename-safe. #
        # If they're not, e.g. if they contain slashes, you must define a rulestring() #
        # function that normalizes inputted rulestrings to be filename-safe. #
        # Your main() function will be passed this new rulestring, not the original. #

        <[ARGS]>
        NAME: The name, to be separated from a rulestring by two colons, that users will invoke your script with from {prefix}sim.
        BLURB: A short (10-to-90-character) description of your script and the rulefile it generates.
        """
        if not blurb:
            blurb = None
        attachment = ctx.message.attachments[0]
        file = await attachment.to_file()
        approved, should_ping = self.bot.approve_asset(file, blurb, ctx.author, 'generator', name=name)
        if approved:
            code = await attachment.read()
            await self._insert_generator(
                name, ctx.author.id, code,
                await self.loop.run_in_executor(
                    None,
                    marshal.dumps,
                    await self.loop.run_in_executor(None, compile, code, '<custom>', 'exec', 0, False, 2)
                ),
                blurb
            )
            self.gencache = None
            await ctx.thumbsup(ctx.author, f'Generator {name} was approved!', should_ping)
        await ctx.thumbsdown(ctx.author, f'Generator {name} was rejected or not parsable.', should_ping, override=False)

    @mutils.command('Show uploaded generators')
    async def generators(self, ctx, text=None, *, flags: mutils.parse_flags = None):
        """
        # If no argument is passed, displays all generators (paginated by tens). #
        <[ARGS]>
        GENERATOR: Generator's name. If a generator by this name (case-sensitive) has been uploaded, displays its info and gives its file.
        [or]
        MEMBER: If the member mentioned is present in the server, shows generators uploaded by them.

        <[FLAGS]>
        -rule: A rulestring. If the string passed above is a generator name, then attached to Caterer's response (instead of the generator's Python file) will be a rulefile generated by running the named generator on this rulestring.
        """
        if flags is None:
            flags = {}
        if self.gencache is None:
            self.gencache = [
                {'name': i['name'], 'uploader': i['uploader'], 'blurb': i['blurb'], 'plaintext': i['plaintext']}
                for i in
                await self.bot.pool.fetch(f'''SELECT DISTINCT ON (name) name, uploader, plaintext, blurb FROM algos''')
            ]
        if text is None:
            offset = 0
            say, msg = ctx.send, None
            while True:
                msg = await say(embed=discord.Embed(
                    title='Rules',
                    description='\n'.join(
                        f"• {i['name']} ({get_member_bismuth(ctx.guild, i['uploader'])}): {i['blurb']}"
                        for i in islice(self.gencache, offset, offset + 10)
                    )
                )) or msg
                say = msg.edit
                left, right = await mutils.get_page(ctx, msg)
                if left:
                    offset = max(0, offset - 10)
                elif right:
                    offset += offset + 10 < len(self.gencache) and 10
        try:
            member = await commands.MemberConverter().convert(ctx, text)
        except commands.BadArgument:
            if 'rule' in flags:
                with io.StringIO() as s:
                    rulestring = await self.write_rule_from_generator(text, flags['rule'], s)
                    s.seek(0)
                    return await ctx.send(file=discord.File(s, rulestring + '.rule'))
            gen = next(d for d in self.gencache if d['name'] == text)
            with io.StringIO(gen['plaintext']) as s:
                s.seek(0)
                return await ctx.send(embed=discord.Embed(
                    title=gen['name'],
                    description=f"Uploader: {self.bot.get_user(gen['uploader'])}\nBlurb: {gen['blurb']}"
                ),
                    file=discord.File(s, gen['name'] + '.py')
                )
        else:
            return await ctx.send(embed=discord.Embed(
                title=f'Generators by {member}',
                description='\n'.join(
                    f"• {d['name']}: {d['blurb']}"
                    for d in self.gencache
                    if d['uploader'] == member.id
                )
            ))

    @mutils.command('Generates a *.rule file with CAViewer')
    async def generate_apgtable(self, ctx, rule, name):
        """
        # Generates an apgtable for apgsearch with CAViewer. #
        <[ARGS]>
        RULE: The rule for CAViewer to generate the ruletable for
        NAME: The name of the outputted rulefile
        """

        preface = f'{self.dir}/resources/bin/CAViewer'

        p = subprocess.Popen(f"{preface} apgtable -r {rule} -o {self.dir}/resources/{name}.rule".split(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.communicate()

        # An error occured
        if out[1].decode("utf-8"): return await ctx.send(f'`{out[1].decode("utf-8")}`')

        with open(f"{self.dir}/resources/{name}.rule") as f:
            return await ctx.send(file=discord.File(f, name + '.rule'))

    @mutils.command()
    async def delgen(self, ctx, name):
        if not await self.bot.is_owner(ctx.author):
            return
        try:
            await self.bot.pool.execute('''DELETE FROM algos WHERE name = $1::text''', name)
        except:
            await ctx.thumbsdown()
            raise
        self.gencache = None
        await ctx.thumbsup()

    @mutils.command()
    async def updatepyc(self, ctx):
        if not await self.bot.is_owner(ctx.author):
            return
        for plaintext, name in await self.bot.pool.fetch('''SELECT plaintext, name FROM algos'''):
            await self.bot.pool.execute(
                '''
              UPDATE algos
              SET module=$1::bytea
              WHERE name=$2::text
              ''',
                await self.loop.run_in_executor(None,
                                                marshal.dumps,
                                                await self.loop.run_in_executor(None,
                                                                                compile,
                                                                                plaintext, f"<generator '{name}'>",
                                                                                'exec'
                                                                                ),
                                                ),
                name
            )
        await ctx.thumbsup()


def setup(bot):
    bot.add_cog(CA(bot))


def get_member_bismuth(guild, *args):
    discrim = str(guild.get_member(*args))
    if '﷽' in discrim:
        return 'bismuth'
    return discrim
