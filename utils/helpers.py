"""Utility functions for C2B generated bots"""
import discord
from discord.ext import commands
import random
import datetime

def create_embed(title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Create a styled embed"""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.timestamp = datetime.datetime.now()
    return embed

def format_error(error: str) -> discord.Embed:
    """Create error embed"""
    return create_embed("❌ エラー", error, discord.Color.red())

def format_success(message: str) -> discord.Embed:
    """Create success embed"""
    return create_embed("✅ 成功", message, discord.Color.green())

def random_color() -> discord.Color:
    """Generate random color"""
    return discord.Color.from_rgb(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )
