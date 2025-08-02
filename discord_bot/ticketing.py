import os
import discord
from datetime import datetime
import asyncio
import aiohttp
import requests
from concurrent.futures import ThreadPoolExecutor

import logging

from discord.ui import View, Button
from discord import ButtonStyle

from .config import *

from tt_calendar.models import Event


# ====================================================================================================================
# ====================================================================================================================
#                                                         Views
# ====================================================================================================================
# ====================================================================================================================


class OverlapTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="🗑️ Neues Event löschen", style=ButtonStyle.primary, custom_id="ticket_delete_new")
    async def delete_new_event(self, interaction: discord.Interaction, button: Button):
        await handle_overlap_resolution(interaction, approve=False)

    @discord.ui.button(label="🗑️ Bestehendes Event löschen", style=ButtonStyle.blurple, custom_id="ticket_delete_existing")
    async def delete_existing_event(self, interaction: discord.Interaction, button: Button):
        await handle_overlap_resolution(interaction, approve=True)

    @discord.ui.button(label="🛠️ Sofort schließen (Vorstand)", style=ButtonStyle.secondary	, custom_id="ticket_sudo_close")
    async def sudo_close(self, interaction: discord.Interaction, button: Button):
        # Optional: check if the user has mod/admin role
        if not any(r.id in guild_roles["vorstand"] for r in interaction.user.roles): # type: ignore
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return

        # await interaction.response.send_message('Wird geschlossen…', ephemeral=True)
        await interaction.response.send_modal(ConfirmSudoCloseModal(self.bot))

class SizeTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="✅ Genehmigen", style=ButtonStyle.success, custom_id="size_approve")
    async def approve_size(self, interaction: discord.Interaction, button: Button):
        await handle_size_resolution(interaction, approve=True)

    @discord.ui.button(label="❌ Ablehnen", style=ButtonStyle.danger, custom_id="size_deny")
    async def deny_size(self, interaction: discord.Interaction, button: Button):
        await handle_size_resolution(interaction, approve=False)


class CloseOnlyTicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="✅ Ticket schließen", style=ButtonStyle.secondary, custom_id="ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        from .ticketing import close  # or adjust import as needed
        await close(interaction)



from discord.ui import Modal, TextInput

class ConfirmSudoCloseModal(Modal, title="⚠️ Ticket wirklich schließen?"):
    def __init__(self, bot):
        super().__init__(timeout=60)
        self.bot = bot

        self.confirm = TextInput(
            label="Bitte tippe 'JA' zum Bestätigen",
            placeholder="JA",
            required=True,
            max_length=5
        )
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.strip().lower() == "ja":
            await sudoclose(self.bot, interaction)
        else:
            await interaction.response.send_message("❌ Nicht bestätigt. Ticket bleibt offen.", ephemeral=True)



# ====================================================================================================================
# ====================================================================================================================
#                                                    Tickets
# ====================================================================================================================
# ====================================================================================================================

async def get_member_safely(guild, uid):
    member = guild.get_member(uid)
    if not member:
        try:
            member = await guild.fetch_member(uid)
        except Exception as e:
            logging.error(f"❌ Could not fetch member {uid}: {e}")
    return member



async def create_ticket(bot, creator_id: int, overlapped_member_id: int | None = None, new_event: Event | None = None, existing_event: Event | None = None):
    """
    Creates a system ticket channel with the given participants.

    :param bot: The bot instance.
    :param channel_name: Name of the ticket channel (e.g. "overlap-ab12cd34").
    :param participants: List of discord.Member to invite into the ticket.
    :param info_lines: Lines of text (strings) to display in the opening embed.
    :param category_id: Discord category ID to create the channel under.
    :param ping_role: Optional role to mention (e.g. Vorstand).
    """
    
    guild = bot.get_guild(guild_id)
    category = guild.get_channel(int(ticket_category_id))
    creator = await get_member_safely(guild, creator_id)

    bot_role = guild.get_role(guild_roles["bot"])

    timestamp = datetime.now().strftime("%d%m%y-%H:%M")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        bot_role: discord.PermissionOverwrite(read_messages=True),
        creator: discord.PermissionOverwrite(read_messages=True),
    }

    for role_id in guild_roles["vorstand"]:
        role = guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True)

    if overlapped_member_id:
        assert new_event
        assert existing_event
        overlapped_member = await get_member_safely(guild, overlapped_member_id)

        channel_name = f"doppelbuchung-{creator.name.lower()}-{timestamp}"
        description = f"""
{creator.name} möchte ein überschneidendes Event anlegen.

🆕 Neues Event: **{new_event.name}**
📅 {new_event.start_time.strftime('%d.%m.%Y %H:%M')} – {new_event.end_time.strftime('%H:%M')}

🛑 Bestehendes Event: **{existing_event.name}**
📅 {existing_event.start_time.strftime('%d.%m.%Y %H:%M')} – {existing_event.end_time.strftime('%H:%M')}

Bitte besprecht hier, ob das Event verschoben werden soll, ob das bestehende Event ersetzt werden kann oder beide bestehen bleiben können.
"""

        overwrites[overlapped_member] = discord.PermissionOverwrite(read_messages=True)

        view = OverlapTicketView(bot)

    else:
        assert new_event
        channel_name = f"vereinsevent-{creator.name.lower()}-{timestamp}"
        event_date = new_event.start_time.strftime('%Y-%m-%d')
        event_time = f"{new_event.start_time.strftime('%H:%M')}–{new_event.end_time.strftime('%H:%M')}"
        creator_name = new_event.user.username.lower().replace(" ", "-")
        short_name = new_event.name.lower().replace(" ", "-")[:30]
        
        description = (
            f"{new_event.name}\n"
            f"{new_event.description}\n"
            f"\n"
            f"\n"
            f"🗓️ {event_date}\n"
            f"🕒 {event_time}\n"
            f"👤 {new_event.user.username}\n"
            f"🔓 {new_event.publicity.name}\n"                                            # type: ignore
            f"🪑 {', '.join([r.table.name for r in new_event.reservations]) or 'Keine'}\n\n"    # type: ignore
            f"**Begründungspflicht:**\n"
            f"Dieses Event beansprucht mehr als drei Tische und muss vom Vorstand bestätigt werden.\n"
            f"Bitte beschreibe hier den Rahmen und Zweck des Events."
        )

        view = SizeTicketView(bot)


    # Create the channel
    ticket_channel = await category.create_text_channel(channel_name, overwrites=overwrites, position=0)

    # Build the embed
    embed = discord.Embed(
        title="🎫 Automatisches Ticket",
        description=description,
        color=discord.Color.blue()
    )
    vorstand_roles = [guild.get_role(rid) for rid in guild_roles["vorstand"]]
    vorstand_roles = [r for r in vorstand_roles if r is not None]

    mentions = f"{creator.mention} " + " ".join(r.mention for r in vorstand_roles)
    if overlapped_member_id:
        mentions += f" {overlapped_member.mention}"
    await ticket_channel.send(f"{mentions}", embed=embed, view=view)

    return ticket_channel.id


# ==============================================================================
#                                  SUDOCLOSE
# ==============================================================================

async def sudoclose(bot, interaction):
    await interaction.response.send_message('Closing this ticket in 5 seconds...')
    await asyncio.sleep(5)
    try:
        await close_ticket_channel(bot, interaction.channel)
    except discord.Forbidden:
        await interaction.response.send_message("*Fehler: Fehlende Berechtigungen. Bitte dem Vorstand melden.*", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("*Fehler: Wahrscheinlich gerade Internetproblem. Bitte später nochmal probieren.*", ephemeral=True)


# ==============================================================================
#                                    CLOSE
# ==============================================================================

async def close(interaction):

    messages = [message async for message in interaction.channel.history(oldest_first=True,limit=1)]
    first_message = messages[0]

    if first_message:
        ticket_opener_mention = first_message.mentions[0].mention  # Get the mention of the ticket opener from the first message

        confirm_message = await interaction.channel.send(f'- CloseRequest - \n'
                                         f'{ticket_opener_mention}, der Vorstand möchte dieses Ticket schließen.\n'
                                         f'Lies dir erst die Antworten durch und checke, dass alles geklärt ist.\n'
                                         f'Reagiere dann mit 👍, um zuzustimmen und diesen Kanal zu löschen.')
        await confirm_message.add_reaction('👍')
        if not interaction.response.is_done():
            await interaction.response.send_message("done.", ephemeral=True)

    else:
        await interaction.response.send_message("There was a problem fetching the ticket opener's information.", ephemeral=True)



# ==============================================================================
#                                  CLOSE REACTION
# ==============================================================================

async def reaction_close_check(bot, payload):
    try:
        guild = bot.get_guild(guild_id)
        user = guild.get_member(payload.user_id)
        message_id = payload.message_id
        channel_id = payload.channel_id
        channel = guild.get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        emoji = payload.emoji
    except:
        logging.info("Error on raw reaction. Must not be the right one.")
        return


    if user == bot.user:
        return

    
    if not message.content.startswith('- CloseRequest -'):
        return
    
    logging.info(f'A Reaction has been added to a CloseRequest inside a ticket channel.')

    if not emoji.name == '👍':
        logging.info(f'Emoji was not a thumbs up.')
        return
    
    if not user.name == message.mentions[0].name:
        logging.info(f'Mentioned user {message.mentions[0].name} and reacting user {user} did not match')
        return
    

    await channel.send('Schließung bestätigt. Kanal wird in 10 Sekunden gelöscht.')
    await asyncio.sleep(10)  # Optional delay
    try:
        await close_ticket_channel(bot, channel)
    except:
        logging.info("ticket already deleted")



async def close_ticket_channel(bot, channel):
    log_file_path = await create_ticket_log(channel)
    log_file = discord.File(log_file_path, filename=log_file_path)
    guild = bot.get_guild(guild_id)
    logs_channel = guild.get_channel(ticket_log_id)
    await logs_channel.send(f'Log for closed ticket {channel.name}', file=log_file)
    os.remove(log_file_path)
    try:
        await channel.delete()
    except discord.Forbidden:
        await channel.send("*Fehler: Fehlende Berechtigungen. Bitte dem Vorstand melden.*")
    except discord.HTTPException:
        await channel.send("*Fehler: Wahrscheinlich gerade Internetproblem. Bitte später nochmal probieren.*")




async def create_ticket_log(channel):
    # Assuming you want to log the channel name and the final message content
    log_content = f"Ticket Closed: {channel.name}\n" \
                  f"Closed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    messages = [msg async for msg in channel.history(limit=100)]  # newest to oldest
    for message in reversed(messages):  # oldest to newest
        log_content += f"{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {message.author.display_name}: {message.content}\n"

    # async for message in channel.history(limit=100):  # adjust the limit as necessary
    #     log_content += f"{message.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {message.author.display_name}: {message.content}\n"

    # Save to a .txt file
    file_name = f"{channel.name}_log.txt"
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write(log_content)
    return file_name



# ====================================================================================================================
# ====================================================================================================================
#                                                overlap resolutions
# ====================================================================================================================
# ====================================================================================================================


async def handle_overlap_resolution(interaction, approve: bool):
    await interaction.response.defer(ephemeral=True)

    # Check if user has valid role
    guild = interaction.guild
    member = await get_member_safely(guild, interaction.user.id)
    if not member:
        member = await guild.fetch_member(interaction.user.id)

    
    is_vorstand = any(
        role.id in guild_roles["vorstand"] or role.id in guild_roles["admin"]
        for role in member.roles
    )

    data = {
        "discord_user_id": interaction.user.id,
        "channel_id": interaction.channel.id,
        "approve": approve,
        "is_vorstand": is_vorstand
    }

    try:
        server_name = os.getenv("SERVER_NAME")
        response = requests.post(f"https://{server_name}/api/resolve_overlap", json=data)
        result = response.json()

        if response.status_code == 200:
            await interaction.channel.send(f"🗑️ {result['message']}")

            await close(interaction)
        else:
            await interaction.channel.send(f"❌ {result.get('message', 'Fehler beim Löschen.')}")

    except Exception as e:
        logging.error(f"[handle_overlap_resolution] {e}")
        await interaction.followup.send("❌ Serverfehler beim Löschen.", ephemeral=True)


# ====================================================================================================================
# ====================================================================================================================
#                                                   size resolutions
# ====================================================================================================================
# ====================================================================================================================


async def handle_size_resolution(interaction, approve: bool):
    await interaction.response.defer(ephemeral=True)

    # Check if user has valid role
    guild = interaction.guild
    member = await get_member_safely(guild, interaction.user.id)
    if not member:
        member = await guild.fetch_member(interaction.user.id)

    is_vorstand = any(
        role.id in guild_roles["vorstand"] or role.id in guild_roles["admin"]
        for role in member.roles
    )

    data = {
        "channel_id": interaction.channel.id,
        "approve": approve,
        "is_vorstand": is_vorstand
    }

    try:
        server_name = os.getenv("SERVER_NAME")
        response = requests.post(f"https://{server_name}/api/resolve_size", json=data)
        result = response.json()

        if response.status_code == 200:
            await interaction.channel.send(f"📌 {result['message']}")
            await close(interaction)
        else:
            await interaction.channel.send(f"❌ {result.get('message', 'Fehler beim Aktualisieren.')}")

    except Exception as e:
        logging.error(f"[handle_size_resolution] {e}")
        await interaction.followup.send("❌ Serverfehler beim Bearbeiten der Größe.", ephemeral=True)



# ====================================================================================================================
# ====================================================================================================================
#                                                   Ticket resolving
# ====================================================================================================================
# ====================================================================================================================




async def change_resolved_ticket_view(bot, channel_id: int):
    guild = bot.get_guild(guild_id)
    if not guild:
        logging.info("❌ Guild not found")
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        logging.info("❌ Channel not found")
        return

    try:
        async for message in channel.history(oldest_first=True, limit=1):
            await message.edit(view=CloseOnlyTicketView(bot))
            return

        logging.error(f"⚠️ No message found in channel {channel.name} to edit.")
    except Exception as e:
        logging.error(f"❌ Failed to replace view: {e}")