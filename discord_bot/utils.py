from .config import guild_id, guild_roles
from .bot import bot
import discord


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


async def send_message_in_event_thread(channel_id, message_id, message: str):
    """
    Sends a reminder message in the event's discussion thread.
    - Fetches the correct channel using the event's game category.
    - Retrieves the original message from `discord_post_id`.
    - Sends a reminder message in the associated thread.
    """

    channel = bot.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        print(f"❌ Could not retrieve channel {channel_id}.")
        return

    try:
        # Fetch the event message inside the correct category channel
        post = await channel.fetch_message(message_id)
        thread = post.thread  # Get the discussion thread from the message

        if thread:
            await thread.send(message)
            print(f"✅ Sent reminder in thread for event.")
        else:
            print(f"⚠️ No thread found for event.")

    except discord.NotFound:
        print(f"❌ Message {message_id} not found in {channel.name}")
    except discord.Forbidden:
        print(f"❌ No permission to fetch message {message_id} in {channel.name}")
    except discord.HTTPException as e:
        print(f"❌ HTTP error while fetching message {message_id}: {e}")


