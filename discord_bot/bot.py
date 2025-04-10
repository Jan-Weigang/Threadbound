import discord
from discord.ext import commands, tasks

from .config import discord_token, kalender_channels, guild_id, guild_roles
from .ticketing import TicketCloseView, reaction_close_check


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
    print(f'{bot.user} has connected to Discord guild {guild.name}!')

    if guild:
        await guild.chunk()
        print(f"✅ Chunked {guild.name} – {len(guild.members)} members cached.")
    else:
        print("❌ Guild not found. Check GUILD_ID.")

    bot.add_view(TicketCloseView(bot)) 



# ==============================================================================
#                                 Event Threads
# ==============================================================================


@bot.event
async def on_message(message):
    print("I am running on_message")
    # Check if the message author is the bot itself; if so, return early
    if message.author != bot.user:
        return  # Skip processing if the message is from the bot itself

    # Check if the message was posted in one of the Kalenderchannels
    if message.channel.id in kalender_channels.values():
        
        # Extract event_id from the embed
        event_id = None
        if message.embeds:
            embed = message.embeds[0]
            footer_text = embed.footer.text
            if footer_text and "Event ID: " in footer_text:
                event_id = footer_text.split("Event ID: ")[-1][:12]  # Get the 12 characters after "Event ID: "

        if not event_id:
            print("Event ID not found in the embed footer.")
            return

        # Create the buttons
        view = discord.ui.View()  # View holds all the interactive components
        view.add_item(discord.ui.Button(label="Ich bin dabei!", style=discord.ButtonStyle.success, custom_id="attend"))
        # view.add_item(discord.ui.Button(label="Nur vielleicht...", style=discord.ButtonStyle.success, custom_id="maybe"))
        view.add_item(discord.ui.Button(label="Ich kann nicht.", style=discord.ButtonStyle.primary, custom_id="not_attend"))

        server_name = os.getenv('SERVER_NAME')
        ics_url = f"https://{server_name}/ics/event/{event_id}"
        print(ics_url)
        view.add_item(discord.ui.Button(label="ICS", style=discord.ButtonStyle.link, url=ics_url))



        # Check if the message contains only an embed
        if message.embeds and not message.content:
            embed_title = message.embeds[0].title if message.embeds[0].title else "Discussion"
            thread_name = f"Discussion for {embed_title[:50]}"  # Use the embed title as the thread name
        else:
            # Use the message content as the thread name (limit to 50 characters)
            thread_name = f"Discussion for {message.content[:50]}" if message.content else "Discussion"

        # Create a thread for discussion if the channel allows it
        if isinstance(message.channel, discord.TextChannel):
            try:
                # Create the thread attached to the message
                thread = await message.create_thread(name=thread_name, auto_archive_duration=1440)  # 1440 is for 24-hour archive duration
                print(f"Thread '{thread_name}' created successfully.")
            except discord.Forbidden:
                print("Bot does not have permission to create threads in this channel.")
            except discord.HTTPException as e:
                print(f"Failed to create thread: {e}")

        # Create a thread for discussion if the channel allows it
        if isinstance(message.channel, discord.TextChannel):
            try:
                # Create the thread attached to the message
                await message.edit(view=view)
                print(f"Thread '{thread_name}' created successfully.")
            except discord.Forbidden:
                print("Bot does not have permission to create threads in this channel.")
            except discord.HTTPException as e:
                print(f"Failed to create thread: {e}")



# ==============================================================================
#                                 Button Presses
# ==============================================================================

@bot.event
async def on_interaction(interaction: discord.Interaction):
    print("I am running on_interaction")
    await interaction.response.defer(ephemeral=True)
    
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
    print("test")
    from .utils import get_nickname
    # Prepare data for the Flask API request

    nickname = await get_nickname(interaction.user.id)

    data = {
        "discord_user_id": interaction.user.id,
        "message_id": interaction.message.id,
        "action": action,
        "username": nickname
    }

    # Call the Flask API endpoint
    try:
        server_name = os.getenv('SERVER_NAME')
        response = requests.post(f"https://{server_name}/api/attendance", json=data)
        result = response.json()

        print("json result:")
        print(result)

        # Process the API response
        if response.status_code == 200:
            pass

        else:
            message = result.get('message', 'No message provided')
            print(f"Error from API: {message}")

    except Exception as e:
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
        print(f"Error in handling interaction: {e}")




@bot.event
async def on_raw_reaction_add(payload):
    logging.info("Checking a raw reaction")
    await reaction_close_check(bot, payload)


# Function to start the bot
async def run_discord_bot():
    await bot.start(discord_token)  # Replace with your bot token