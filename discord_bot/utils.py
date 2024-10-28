import discord
from .config import guild_id, guild_roles
from .bot import bot


async def get_nickname(discord_user_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    
    member = guild.get_member(discord_user_id)
    if member:
        return member.nick or member.name 
    else:
        return None


async def is_guild_role(discord_user_id: int, role_string):
    discord_user_id = int(discord_user_id)
    guild = bot.get_guild(guild_id)

    if not guild:
        return False
    
    member = guild.get_member(discord_user_id)
    if not member:
        return False
    
    role_id = guild_roles.get(role_string)
    if role_id is None:
        raise ValueError(f"Role '{role_string}' does not exist in guild_roles.")

    role = guild.get_role(role_id)
    if role and role in member.roles:
        return True 
    else:
        return False



