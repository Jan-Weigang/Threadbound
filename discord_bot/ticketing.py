import os
import discord
from datetime import datetime
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

import logging

from discord.ui import View, Button
from discord import ButtonStyle

from .config import *

class TicketCloseView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="✅ Schließen", style=ButtonStyle.success, custom_id="ticket_close")
    async def user_close(self, interaction: discord.Interaction, button: Button):
        await close(self.bot, interaction)

    @discord.ui.button(label="🛠️ Sofort schließen (Vorstand)", style=ButtonStyle.danger, custom_id="ticket_sudo_close")
    async def sudo_close(self, interaction: discord.Interaction, button: Button):
        # Optional: check if the user has mod/admin role
        if not any(r.id == guild_roles["vorstand"] for r in interaction.user.roles): # type: ignore
            await interaction.response.send_message("❌ Keine Berechtigung.", ephemeral=True)
            return

        # await interaction.response.send_message('Wird geschlossen…', ephemeral=True)
        await interaction.response.send_modal(ConfirmSudoCloseModal(self.bot))


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


async def get_member_safely(guild, uid):
    member = guild.get_member(uid)
    if not member:
        try:
            member = await guild.fetch_member(uid)
        except Exception as e:
            print(f"❌ Could not fetch member {uid}: {e}")
    return member



async def create_ticket(bot, creator_id: int, overlapped_member_id: int = None): # type: ignore
    """
    Creates a system ticket channel with the given participants.

    :param bot: The bot instance.
    :param channel_name: Name of the ticket channel (e.g. "overlap-ab12cd34").
    :param participants: List of discord.Member to invite into the ticket.
    :param info_lines: Lines of text (strings) to display in the opening embed.
    :param category_id: Discord category ID to create the channel under.
    :param ping_role: Optional role to mention (e.g. Vorstand).
    """

    print(f"{overlapped_member_id=} {creator_id=}")


    guild = bot.get_guild(guild_id)
    print(guild.name)
    category = guild.get_channel(int(ticket_category_id))
    creator = await get_member_safely(guild, creator_id)

    print(f"🔍 Creator: {creator} ({creator_id})")

    bot_role = guild.get_role(guild_roles["bot"])
    vorstand_role = guild.get_role(guild_roles["vorstand"])
    beirat_role = guild.get_role(guild_roles["beirat"])

    timestamp = datetime.now().strftime("%d%m-%H%M")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        vorstand_role: discord.PermissionOverwrite(read_messages=True),
        bot_role: discord.PermissionOverwrite(read_messages=True),
        creator: discord.PermissionOverwrite(read_messages=True),
    }

    if overlapped_member_id:
        print("if overlapped")
        
        overlapped_member = await get_member_safely(guild, overlapped_member_id)

        print(f"{overlapped_member=} {creator=}")

        channel_name = f"doppelbuchung-{creator.name.lower()}-{timestamp}"
        description = (
            f"{creator.name} möchte gerne ein überschneidendes Event anlegen.\n"
            "Bitte besprecht hier, welche Änderungen nötig sind, damit beide stattfinden können, oder ob das bisherige Event überschrieben werden soll."
        )

        overwrites[overlapped_member] = discord.PermissionOverwrite(read_messages=True)

    else:
        channel_name = f"{creator.name}-vereinsevent-{timestamp}"
        description = (
            "Für diese Reservierung wurden mehr als 3 Tische ausgewählt.\n"
            "Dies muss vom Vorstand genehmigt werden. Erkläre hier kurz dein Event."
        )


    # Create the channel
    ticket_channel = await category.create_text_channel(channel_name, overwrites=overwrites, position=0)

    # Build the embed
    embed = discord.Embed(
        title="🎫 Automatisches Ticket",
        description=description,
        color=discord.Color.blue()
    )

    mentions = f"{creator.mention} {vorstand_role.mention}"
    if overlapped_member_id:
        mentions += f" {overlapped_member.mention}"
    await ticket_channel.send(f"{mentions}", embed=embed, view=TicketCloseView(bot))

    return ticket_channel.id


# ==============================================================================
#                                  SUDOCLOSE
# ==============================================================================

async def sudoclose(bot, interaction):
    if 'ticket-' in interaction.channel.name:
        await interaction.response.send_message('Closing this ticket in 5 seconds...')
        await asyncio.sleep(5)
        try:
            await close_ticket_channel(bot, interaction.channel)
        except discord.Forbidden:
            await interaction.response.send_message("*Fehler: Fehlende Berechtigungen. Bitte dem Vorstand melden.*", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("*Fehler: Wahrscheinlich gerade Internetproblem. Bitte später nochmal probieren.*", ephemeral=True)
    else:
        await interaction.response.send_message('*Dies ist kein Ticket-Kanal.*', ephemeral=True)


# ==============================================================================
#                                    CLOSE
# ==============================================================================

async def close(bot, interaction):

    if 'ticket-' not in interaction.channel.name:
        await interaction.response.send_message('This command can only be used in ticket channels.', ephemeral=True)
        return

    messages = [message async for message in interaction.channel.history(oldest_first=True,limit=1)]
    first_message = messages[0]

    if first_message:
        ticket_opener_mention = first_message.mentions[0].mention  # Get the mention of the ticket opener from the first message

        confirm_message = await interaction.channel.send(f'- CloseRequest - \n'
                                         f'{ticket_opener_mention}, der Vorstand möchte dieses Ticket schließen.\n'
                                         f'Lies dir erst die Antworten durch und checke, dass alles geklärt ist.\n'
                                         f'Reagiere dann mit 👍, um zuzustimmen und diesen Kanal zu löschen.')
        await confirm_message.add_reaction('👍')
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
    
    if 'ticket-' not in channel.name:
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
    await close_ticket_channel(bot, channel)



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