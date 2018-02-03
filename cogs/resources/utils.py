import inspect

import discord
from discord.ext import commands

from .import cmd

class Group(commands.Group):
    
    def __init__(self, **attrs):
        super().__init__(**attrs)
    
    def command(self, *args, **kwargs):
        def decorator(func):
            result = commands.command(*args, **kwargs)(func)
            result.aliases = cmd.aliases.get(f'{self.qualified_name} {result.name}') or []
            self.add_command(result)
            return result
        return decorator

    def group(self, *args, **kwargs):
        def decorator(func):
            result = commands.group(*args, **kwargs)(func)
            result.aliases = cmd.aliases.get(self.qualified_name + result.name) or []
            self.add_command(result)
            return result
        return decorator

def command(name=None, cls=None, **attrs):
    def decorator(func):
        attrs['aliases'] = cmd.aliases.get(name or func.__name__) or []
        return commands.command(name, cls, **attrs)(func)
    return decorator

def group(name=None, **attrs):
    return command(name=name, cls=Group, **attrs)
