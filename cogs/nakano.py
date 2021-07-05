# Written by Parcly Taxel / Freywa
# Original code from https://gitlab.com/parclytaxel/Shinjuku/-/blob/master/shinjuku/nakano.py

import re
from math import gcd, isqrt
from collections import Counter
import lifelib
rule_re = re.compile(r"rule\s*=\s*([A-Za-z0-9/_-]+)\s*$", re.M)


def factors(n):
    """Yield the factors of n in ascending order."""
    rtn = isqrt(n)
    smalls = list(filter(lambda k: n % k == 0, range(1, rtn + 1)))
    larges = [n // k for k in smalls]
    if rtn * rtn == n:
        smalls.pop()
    yield from smalls
    yield from reversed(larges)


def analyse(pat_string, rule="b3s23"):
    """Compute cell periods and other statistics of the given oscillator/spaceship (as an RLE or apggcode)
    like the old Oscillizer. The pattern may be in any 2-state isotropic rule not containing B0.
    Return a dictionary containing relevant statistics:
    res["p"] -> period
    res["dxy"] -> displacement
    res["pops"] -> list of successive populations of the object
    res["popstats"] -> (min. population, max. population, average population, sum of populations across a period)
    res["heats"] -> list of successive heats of the object
    res["heatstats"] -> (min. heat, max. heat, average heat, sum of heats across a period)
    res["bb"] -> bounding box (width, height, cell count)

    For oscillators only:
    res["cellperiods"] -> dictionary mapping active cells to their periods
    res["cellpcounts"] -> dictionary mapping seen cell periods to frequency
    res["cellstats"] -> (rotor cells, stator cells, active cells, strict (full-period) rotor cells)
    res["volstats"] -> (volatility, strict volatility)"""

    if m := rule_re.search(pat_string):
        rule = m[1]

    lt = lifelib.load_rules(rule).lifetree(n_layers=1)
    empty = lt.pattern()
    pat = lt.pattern(pat_string)

    res = {}
    lcmp = res["p"] = pat.period
    dxy = res["dxy"] = pat.displacement
    osc = dxy == (0, 0)
    phases = [pat[i] for i in range(lcmp)]
    pops = [phase.population for phase in phases]
    heats = [(phase ^ phase[1]).population for phase in phases]

    sp = sum(pops)
    sh = sum(heats)

    res["pops"] = pops
    res["popstats"] = (min(pops), max(pops), sp / lcmp, sp)
    res["heats"] = heats
    res["heatstats"] = (min(heats), max(heats), sh / lcmp, sh)

    if osc:
        cellperiods = {}
        pcounts = Counter()
        remcells = sum(phases, start=empty)
        actives = remcells.population
        width, height = remcells.bounding_box[2:]
        res["bb"] = (width, height, width * height)
        for subp in factors(lcmp):
            nremcells = sum((phase ^ phase[subp] for phase in phases), start=empty)
            if subpcells := remcells - nremcells:
                cellperiods.update({(x, y): subp for (x, y) in subpcells.coords().tolist()})
                pcounts[subp] = subpcells.population
                remcells -= subpcells

        res["cellperiods"] = cellperiods
        res["cellpcounts"] = [(p, pcounts[p]) for p in sorted(pcounts, reverse=True)]

        stators = pcounts[1]
        rotors = actives - stators
        strict_rotors = min(rotors, pcounts[lcmp])

        res["cellstats"] = (rotors, stators, actives, strict_rotors)
        res["volstats"] = (rotors / actives, strict_rotors / actives)
        res["tempstats"] = (sh / (lcmp * actives), sh / (lcmp * rotors) if rotors else 0)
    else:
        bb = max((pat[i].bounding_box[2:] for i in range(lcmp)), key=lambda x: x[0] * x[1])
        res["bb"] = (bb[0], bb[1], bb[0] * bb[1])

    return res


def speedstring(dmaj, dmin, period):
    """Return a short string describing the speed with the given parameters.
    Conditions are dmaj >= dmin >= 0, dmaj > 0, period >= 1."""
    if dmaj > dmin > 0:
        numerator = f"({dmaj},{dmin})"
        terminator = ""
    elif dmaj == dmin:
        numerator = f"{dmaj}" if dmaj > 1 else ""
        terminator = "d"
    else:
        numerator = f"{dmaj}" if dmaj > 1 else ""
        terminator = "o"
    denominator = f"/{period}" if period > 1 else ""
    return f"{numerator}c{denominator}{terminator}"


def resultprint(res):
    """Pretty-print the summary statistics of the given results dictionary.
    The formatting for oscillators closely matches the old Oscillizer."""
    result_string = ""

    period = res["p"]
    if res["dxy"] == (0, 0):
        result_string += (f"P{period} oscillator" if period > 1 else "still life") + "\n"
        result_string += "Cell periods:\n"
        for (cp, count) in res["cellpcounts"]:
            result_string += f"p{cp} – {count}\n"

        minpop, maxpop, avgpop, _ = res["popstats"]
        result_string += f"Population {minpop}–{maxpop}, average {avgpop:.2f}\n"

        rotors, stators, total, strict_rotors = res["cellstats"]
        result_string += f"{rotors} rotor cells ({strict_rotors} full-period), {stators} stator cells, {total} total\n"

        vol, svol = res["volstats"]
        result_string += f"Volatility {vol:.4f} ({svol:.4f} strict)\n"

        minheat, maxheat, avgheat, _ = res["heatstats"]
        result_string += f"Heat {minheat}–{maxheat}, average {avgheat:.2f}\n"

        temp, rtemp = res["tempstats"]
        result_string += f"Temperature {temp:.4f} ({rtemp:.4f} rotor)\n"
    else:
        dx, dy = res["dxy"]
        dmaj, dmin = max(abs(dx), abs(dy)), min(abs(dx), abs(dy))
        unsimp_speed = speedstring(dmaj, dmin, period)
        if (k := gcd(dx, dy, period)) > 1:
            simp_speed = speedstring(dmaj//k, dmin//k, period//k)
            result_string += f"{unsimp_speed} ({simp_speed} simplified) spaceship \n"
        else:
            result_string += f"{unsimp_speed} spaceship\n"

        minpop, maxpop, avgpop, _ = res["popstats"]
        result_string += f"Population {minpop}–{maxpop}, average {avgpop:.2f}\n"

        minheat, maxheat, avgheat, _ = res["heatstats"]
        result_string += f"Heat {minheat}–{maxheat}, average {avgheat:.2f}\n"

    bw, bh, bc = res["bb"]
    result_string += f"Bounding box {bw}×{bh} = {bc}\n"

    return result_string


start_colours = ("ffffff", "1c92cd", "0ab87b", "e86075", "f8f290",
                 "ba4117", "d91e9b", "aeaeae", "bef0e9", "428c28",
                 "6f1044", "76adf4", "2f5963", "d9b790")


def periodmap(cellperiods, outfn="osc.png", scale=16):
    """Save a colour-coded map of the active cells and print the
    corresponding periods. Requires NumPy and Pillow; scale sets
    the size of a cell."""

    import numpy as np
    from PIL import Image

    rng = np.random.default_rng()
    cells = np.array([[c[0], c[1], p] for (c, p) in cellperiods.items()])
    cells[:, 0] -= min(cells[:, 0])
    cells[:, 1] -= min(cells[:, 1])
    width = max(cells[:, 0]) + 1
    height = max(cells[:, 1]) + 1
    unique_periods = np.unique(cells[:, 2])[::-1]

    colourmap = {}
    for (n, p) in enumerate(unique_periods):
        if p == 1:
            colourmap[p] = (0, 0, 0)
        elif n < 14:
            col = [int(start_colours[n][i:i+2], 16) for i in (0, 2, 4)]
            colourmap[p] = tuple(col)
        else:
            colourmap[p] = tuple(rng.integers(16, 240, 3))

    for (k, v) in colourmap.items():
        print(f"p{k} – {v[0]:02x}{v[1]:02x}{v[2]:02x}")

    field = np.full((height+2, width+2, 3), 204, dtype=np.uint8)

    for row in cells:
        field[row[1]+1, row[0]+1, :] = colourmap[row[2]]

    im = Image.fromarray(field)
    im.resize((im.width * scale, im.height * scale), 0).save(outfn)


def n(pat_string, rule="b3s23", outfn="osc.png", scale=16):
    """Interactive function to analyse a pattern and display the results."""
    res = analyse(pat_string, rule)
    resultprint(res)
    if res["dxy"] == (0, 0):
        periodmap(res["cellperiods"], outfn, scale)
