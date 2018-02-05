import asyncio
import concurrent
import inspect

import discord
from discord.ext import commands

from .import cmd

__all__ = ['await_event_or_coro', 'command', 'group']

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
    

## Custom command/group decos with info pointing to cmd.py ##

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
        """Voids 'can't set attribute' when dpy tries assigning aliases"""
        pass

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

def command(name=None, cls=Command, **attrs):
    return lambda func: commands.command(name, cls, **attrs)(func)

def group(name=None, *, invoke_without_command=True, **attrs):
    return command(name=name, cls=Group, invoke_without_command=invoke_without_command, **attrs)
