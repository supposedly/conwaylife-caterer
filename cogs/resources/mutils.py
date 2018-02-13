__all__ = ['await_event_or_coro', 'wait_for_any', 'attrify', 'command', 'group']

# ----------------------------------------------------------------------------------- #

import asyncio
import concurrent

async def await_event_or_coro(bot, event, coro, *, ret_check=None, event_check=None, timeout=None):
    """
    discord.Client.wait_for, but force-cancels on completion of
    :param:coro rather than on a timeout
    """
    future = bot.loop.create_future()
    event_check = event_check or (lambda _: True)
    try:
        listeners = bot._listeners[event.lower()]
    except KeyError:
        listeners = []
        bot._listeners[event.lower()] = listeners
    listeners.append((future, event_check))
    [done], pending = await asyncio.wait([future, coro], timeout=timeout, return_when=concurrent.futures.FIRST_COMPLETED)
    for task in pending:
        task.cancel() # does this even work???
    return {'event' if ret_check(done.result()) else 'coro': done.result()}
    

async def wait_for_any(ctx, events, checks, *, timeout=15.0):
    """
    ctx: Context instance
    events: Sequence of events as outlined in dpy's event reference
    checks: Sequence of check functions as outlined in dpy's docs
    timeout: asyncio.wait timeout
    
    events and checks must be of the same length.
    """
    mapped = dict(zip(events, checks)).items()
    futures = [ctx.bot.wait_for(event, timeout=timeout, check=check) for event, check in mapped]
    [done], pending = await asyncio.wait(futures, loop=ctx.bot.loop, timeout=timeout, return_when=concurrent.futures.FIRST_COMPLETED)
    result = done.result()
    for event, check in mapped:
        try:
            valid = check(result)
        except TypeError: # too many/few arguments
            continue
        if valid:
            return {event: result}
    return None

# ----------------------------------------------------------------------------------- #

def parse_args(args: [str], regex: [compile], defaults: []) -> ([str], [str]):
    """
    Sorts `args` according to order in `regexes`.
    
    If no matches for a given regex are found in `args`, the item
    in `defaults` with the same index is dropped in to replace it.
    
    Extraneous arguments in `args` are left untouched, and the
    second item in this func's return tuple will consist of these
    extraneous args, if there are any.
    """
    assert len(regex) == len(defaults)
    args = list(args)
    new, regex = [], [i if isinstance(i, (list, tuple)) else [i] for i in regex]
    for ri, rgx in enumerate(regex): 
        for ai, arg in enumerate(args):
            if any(k.match(arg) for k in rgx):
                new.append(arg)
                args.pop(ai)
                break
        else: 
             new.append(defaults[ri])
    return new, args
    
def parse_flags(flags: [str], *, prefix='-', delim=':') -> {str: str}:
    """len(delim) == len(prefix) == 1"""
    # I don't remember why or how the generators below work
    # but they do.
    # except when you have an opening quote with a space directly after
    # but who cares about those cases? (aaaagh)
    flags = [i.lstrip(prefix) for i in flags if i.startswith(prefix)]
    openers = (i for i, v in enumerate(flags) if f"{delim}'" in v)
    closers = (i for i, v in enumerate(flags) if v.endswith("'"))
    while True:
        try:
            begin = next(openers)
        except (IndexError, StopIteration):
            break # as if returning flags
        end = begin if flags[begin].endswith("'") else next(closers)
        new = ' '.join(flags[begin:1+end])
        flags[begin:end] = ''
        flags[begin] = new.rstrip("'").replace(f"{delim}'", delim)
    # now just get 'em into a dict
    new = {}
    for v in flags:
        flag, opts = (v+delim[delim in v:]).split(delim, 1)
        new[flag] = opts
    return new

# ----------------------------------------------------------------------------------- #

import dis
import types

CODE_TYPE = type((lambda: None).__code__)

def attrify(func):
    """Assign nested callables to attributes of their enclosing function"""
    for nest in (types.FunctionType(i.argval, globals()) for i in dis.get_instructions(func) if type(i.argval) is CODE_TYPE):
        setattr(func, nest.__name__, nest)
    return func

# ----------------------------------------------------------------------------------- #

def chain(nested):
    """itertools.chain() but leave strings untouched"""
    for i in nested:
        if isinstance(i, (list, tuple)):
            yield from chain(i)
        else:
            yield i

# ------------- Custom command/group decos with info pointing to cmd.py ------------- #

import discord
from discord.ext import commands

from .import cmd

class HelpPropsMixin:
    @property
    def helpsafe_name(self):
        return self.qualified_name.replace(' ', '/')
    
    @property
    def invocation_args(self):
        return cmd.args.get(self.qualified_name, '')
    
    @property
    def aliases(self):
        return cmd.aliases.get(self.qualified_name, [])
    
    @aliases.setter
    def aliases(*_):
        """Eliminates "can't set attribute" when dpy tries assigning aliases"""

class Command(HelpPropsMixin, commands.Command):
    def __init__(self, name, callback, **kwargs):
        self.parent = None
        super().__init__(name, callback, **kwargs)

class Group(HelpPropsMixin, commands.Group):
    def __init__(self, **attrs):
        self.parent = None
        super().__init__(**attrs)
    
    def command(self, *args, **kwargs):
        def decorator(func):
            res = commands.command(cls=Command, *args, **kwargs)(func)
            self.add_command(res)
            return res
        return decorator
    
    def group(self, *args, **kwargs):
        def decorator(func):
            res = commands.group(*args, **kwargs)(func)
            self.add_command(res)
            return res
        return decorator

def command(name=None, brief=None, cls=Command, **attrs):
    return lambda func: commands.command(name or func.__name__, cls, brief=brief, **attrs)(func)

def group(name=None, brief=None, *, invoke_without_command=True, **attrs):
    return command(name=name, brief=brief, cls=Group, invoke_without_command=invoke_without_command, **attrs)
