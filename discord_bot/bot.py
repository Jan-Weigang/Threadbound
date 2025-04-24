import discord
from discord.ext import commands, tasks

from .config import discord_token, guild_id, guild_roles
from .ticketing import OverlapTicketView, SizeTicketView, CloseOnlyTicketView, reaction_close_check


import os, requests, datetime, pytz
import logging



# Set up the bot with required intents
intents = discord.Intents.default()
intents.members = True  # This is required to fetch member data (like nicknames)
intents.messages = True
intents.message_content = True
intents.reactions = True  # To allow the bot to add reactions



bot = commands.Bot(command_prefix='!', intents=intents)

# Event triggered when the bot is ready
@bot.event
async def on_ready():
    guild = bot.get_guild(guild_id)
    assert guild
    logging.info(f'{bot.user} has connected to Discord guild {guild.name}!')

    if guild:
        await guild.chunk()
        logging.info(f"✅ Chunked {guild.name} – {len(guild.members)} members cached.")
    else:
        logging.error("❌ Guild not found. Check GUILD_ID.")

    bot.add_view(OverlapTicketView(bot)) 
    bot.add_view(SizeTicketView(bot))
    bot.add_view(CloseOnlyTicketView(bot)) 



# ==============================================================================
#                                 Event Threads
# ==============================================================================


@bot.event
async def on_message(message):
    # Check if the message author is the bot itself; if so, return early
    if message.author != bot.user:
        return  # Skip processing if the message is from the bot itself

    event_id = None
    if message.embeds:
        embed = message.embeds[0]
        footer_text = embed.footer.text
        if footer_text and "Event ID: " in footer_text:
            event_id = footer_text.split("Event ID: ")[-1][:12]  # Get the 12 characters after "Event ID: "

    if not event_id:
        logging.info("Event ID not found in the embed footer.")
        return

    # Create the buttons
    view = discord.ui.View()  # View holds all the interactive components
    view.add_item(discord.ui.Button(label="Ich bin dabei!", style=discord.ButtonStyle.success, custom_id="attend"))
    # view.add_item(discord.ui.Button(label="Nur vielleicht...", style=discord.ButtonStyle.success, custom_id="maybe"))
    view.add_item(discord.ui.Button(label="Ich kann nicht.", style=discord.ButtonStyle.primary, custom_id="not_attend"))

    server_name = os.getenv('SERVER_NAME')
    ics_url = f"https://{server_name}/ics/event/{event_id}"
    view.add_item(discord.ui.Button(label="ICS", style=discord.ButtonStyle.link, url=ics_url))

    # Check if the message contains only an embed
    if message.embeds:
        print("yeyjlkej")
        embed = message.embeds[0]
        event_date_str = "Unbekannt"
        event_name = message.embeds[0].title if message.embeds[0].title else "Event"

        # Try to get the date from the first field name
        for field in embed.fields:
            if field.name.startswith("📅 "):
                event_date_str = field.name.replace("📅 ", "")
                break

        thread_name = f"📅 {event_date_str[:6]} – {event_name[:40]}"
        print(thread_name)
    else:
        print("nope")
        # Use the message content as the thread name (limit to 50 characters)
        thread_name = f"{message.content[:50]}" if message.content else "Discussion"

    # Create a thread for discussion if the channel allows it
    if isinstance(message.channel, discord.TextChannel):
        try:
            # Create the thread attached to the message
            thread = await message.create_thread(
                name=thread_name, auto_archive_duration=10080)  # 1440 is for 24-hour archive duration
            await thread.send("Teilnahmeknöpfe für den Thread.", view=view)
        except discord.Forbidden:
            logging.error("Bot does not have permission to create threads in this channel.")
        except discord.HTTPException as e:
            logging.error(f"Failed to create thread: {e}")

    # Create a thread for discussion if the channel allows it
    if isinstance(message.channel, discord.TextChannel):
        try:
            # Create the thread attached to the message
            await message.edit(view=view)
        except discord.Forbidden:
            logging.error("Bot does not have permission to create threads in this channel.")
        except discord.HTTPException as e:
            logging.error(f"Failed to create thread: {e}")




# ==============================================================================
#                                 Button Presses
# ==============================================================================

@bot.event
async def on_interaction(interaction: discord.Interaction):

    # TODO CHANGE THIS TO SMARTER BUTTONS
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        return
    
    # Check if the interaction is from a button
    if not interaction.type == discord.InteractionType.component:
        return
    
    assert interaction.data
    custom_id = interaction.data.get('custom_id')


    # ======================================
    #             Function Switch
    # ======================================

    # Map the custom_id to an action
    if custom_id == "attend" or custom_id == "not_attend":
        
        await interact_with_event(interaction, action=custom_id)
    else:
        await interaction.followup.send("Unknown action.", ephemeral=True)
        return
    


async def interact_with_event(interaction, action):
    from .utils import get_nickname
    # Prepare data for the Flask API request

    nickname = await get_nickname(interaction.user.id)

    # Default to the button message
    message_id = interaction.message.id

    # If button message has no embed, try to get the thread's starter message
    if not interaction.message.embeds:
        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            logging.info("button was pressed on a thread")
            try:
                parent = thread.parent
                starter = await parent.fetch_message(thread.id) #type: ignore
                message_id = starter.id
            except discord.NotFound:
                logging.warning("Starter message not found.")


    data = {
        "discord_user_id": interaction.user.id,
        "message_id": message_id,
        "action": action,
        "username": nickname
    }

    # Call the Flask API endpoint
    try:
        server_name = os.getenv('SERVER_NAME')
        response = requests.post(f"https://{server_name}/api/attendance", json=data)
        result = response.json()

        # Process the API response
        if response.status_code == 200:
            pass

        else:
            message = result.get('message', 'No message provided')
            logging.error(f"Error from API while interacting with event: {message}")

    except Exception as e:
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
        logging.error(f"Error in handling interaction: {e}")




@bot.event
async def on_raw_reaction_add(payload):
    logging.info("Checking a raw reaction")
    await reaction_close_check(bot, payload)


# Function to start the bot
async def run_discord_bot():
    await bot.start(discord_token)  # Replace with your bot token