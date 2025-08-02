from .config import guild_id, guild_roles
from .bot import bot
import discord

import logging

async def get_nickname(discord_user_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    
    member = guild.get_member(discord_user_id)
    if member:
        return member.nick or member.global_name or member.name 
    else:
        return None


async def is_guild_role(discord_user_id: int, role_string: str):
    discord_user_id = int(discord_user_id)
    guild = bot.get_guild(guild_id)

    if not guild:
        return False
    
    member = guild.get_member(discord_user_id)
    if not member:
        return False
    
    role_ids = guild_roles.get(role_string)
    if role_ids is None:
        raise ValueError(f"Role '{role_string}' does not exist in guild_roles.")

    member_role_ids = [role.id for role in member.roles]
    return any(role_id in member_role_ids for role_id in role_ids)


async def send_message_in_event_thread(channel_id, message_id, message: str):
    """
    Sends a reminder message in the event's discussion thread.
    - Fetches the correct channel using the event's game category.
    - Retrieves the original message from `discord_post_id`.
    - Sends a reminder message in the associated thread.
    """

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        logging.info(f"❌ Could not retrieve channel {channel_id}.")
        return

    try:
        # Fetch the event message inside the correct category channel
        post = await channel.fetch_message(message_id)
        thread = post.thread  # Get the discussion thread from the message

        if thread:
            await thread.send(message)
        else:
            logging.info(f"⚠️ No thread found for event.")

    except discord.NotFound:
        logging.error(f"❌ Message {message_id} not found in {channel.name}")
    except discord.Forbidden:
        logging.error(f"❌ No permission to fetch message {message_id} in {channel.name}")
    except discord.HTTPException as e:
        logging.error(f"❌ HTTP error while fetching message {message_id}: {e}")


async def add_user_to_event_thread(channel_id: int, message_id: int, user_id: int):
    guild = bot.get_guild(guild_id)  # or fetch dynamically if needed
    assert guild

    channel = guild.get_channel(channel_id)
    message = await channel.fetch_message(message_id) # type: ignore
    thread = message.thread

    if not thread:
        logging.info(f"⚠️ No thread found on message {message_id}")
        return

    user = await bot.fetch_user(user_id)
    await thread.add_user(user)
