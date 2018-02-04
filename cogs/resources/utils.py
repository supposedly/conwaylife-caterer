import asyncio
import concurrent
import inspect

import discord
from discord.ext import commands

from .import cmd

## wait_for that force-cancels on given coro's completion rather than on a timeout ##

async def await_event_or_coro(bot, event, coro, *, ret_check=None, event_check=None, timeout=None):
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
        task.cancel()
    return {'event' if ret_check(done.result()) else 'coro': done.result()}
    

## Custom command/group decos with aliases pointing to cmd.py ##

class Group(commands.Group):
    
    def __init__(self, **attrs):
        super().__init__(**attrs)
    
    def command(self, *args, **kwargs):
        def decorator(func):
            res = commands.command(*args, **kwargs)(func)
            res.parent = self
            res.helpsafe_name = res.qualified_name.replace(" ", "/")
            res.aliases = cmd.aliases.get(res.qualified_name) or []
            res.invocation_args = cmd.args.get(res.qualified_name) or ''
            self.add_command(res)
            return res
        return decorator
    
    def group(self, *args, **kwargs):
        def decorator(func):
            res = commands.group(*args, **kwargs)(func)
            res.parent = self
            res.helpsafe_name = (res.qualified_name.replace(" ", "/"))
            res.aliases = cmd.aliases.get(res.qualified_name) or []
            res.invocation_args = cmd.args.get(res.qualified_name) or ''
            self.add_command(res)
            return res
        return decorator

def command(name=None, cls=None, **attrs):
    return lambda func: commands.command(name, cls, **attrs)(func)

def group(name=None, **attrs):
    return command(name=name, cls=Group, **attrs)
