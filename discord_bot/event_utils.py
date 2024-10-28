import discord
from .config import guild_id, guild_roles
from .bot import bot

from flask import url_for


async def post_event_embed_to_channel(channel_id, embed):
    channel = bot.get_channel(channel_id)
    if channel and isinstance(channel, discord.TextChannel):
        message = await channel.send(embed=embed)
        return message.id  # Return the message ID after sending
    return None  # Return None if something goes wrong


async def delete_event_message_from_discord(channel_id, message_id):
    channel = bot.get_channel(channel_id)
    if channel and isinstance(channel, discord.TextChannel):
        message = await channel.fetch_message(message_id)
        await message.delete()


async def update_event_embed_in_discord(channel_id, new_embed, message_id):
    channel = bot.get_channel(channel_id)
    if  channel and  isinstance(channel, discord.TextChannel):
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=new_embed)
            print("Message updated successfully.")
            return message_id
        except discord.NotFound:
            print("Message not found.")
            return None
        except discord.Forbidden:
            print("Permission to edit message denied.")
            return None
        except discord.HTTPException as e:
            print(f"HTTP error occurred: {e}")
            return None


def get_embed_color_from_event(event):
    hex_color = event.event_type.color.lstrip('#')
    color_int = int(hex_color, 16)  # Convert hex string to integer
    return color_int


def generate_event_embed(event, channel_id, action):
    if action == 'cancel':
        embed = discord.Embed(
            title=f"Abgesagt: {event.name}",
            color=get_embed_color_from_event(event)
        )
    else:
            embed = discord.Embed(
            title=f"📅 {event.name}",
            color=get_embed_color_from_event(event)
        )
    channel = bot.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel):
        guild = channel.guild
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)

        
    thumbnail_url = url_for('serve_thumbnail', filename='thumbnail.png', _external=True)
    print(thumbnail_url)
    embed.set_thumbnail(url=thumbnail_url)

    embed.set_author(name=f"{event.event_type.name} - {event.game_category.name}")

    embed.add_field(name=f"🕒 {event.start_time.strftime('%H:%M')}", value="von", inline=True)
    embed.add_field(name=f"🕓 {event.end_time.strftime('%H:%M')}", value="bis", inline=True)

    embed.add_field(name="", value="", inline=False)

    embed.add_field(name="", value=event.description or "N/A", inline=False)

    embed.add_field(name="", value="", inline=False)
    if not action == 'cancel':
        embed.add_field(name=f"👤 {event.user.username}", value=event.publicity.name, inline=True)
        reserved_tables = ', '.join([reservation.table.name for reservation in event.reservations]) or 'N/A'
        embed.add_field(name="reserviert", value=reserved_tables, inline=True)

        embed.add_field(name="", value="", inline=False)

        # Attendees: Add the list of attendees for the event
        attendees_list = ', '.join([attendee.username for attendee in event.attendees]) or 'Keine Teilnehmer'  # If no attendees, show "Keine Teilnehmer"
        embed.add_field(name="Teilnehmer", value=attendees_list, inline=False)
    
    embed.set_footer(text=f"Event ID: {event.id} - Erstellt:")
    embed.timestamp = event.time_created

    return embed