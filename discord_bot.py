import discord
from discord.ext import commands
from flask import url_for
import os, json, requests

from dotenv import load_dotenv
load_dotenv()


# ======================================
# ============= Variables ==============
# ======================================

discord_token_str = os.getenv('DISCORD_TOKEN')
if not discord_token_str or not isinstance(discord_token_str, str):
    raise EnvironmentError("DISCORD_TOKEN must be a non-empty string")

discord_token = str(discord_token_str)


# Parsing CHANNELS as JSON
kalender_channels_json = os.getenv('CHANNELS')
if not kalender_channels_json:
    raise EnvironmentError("CHANNELS must be defined and cannot be empty")
try:
    kalender_channels = json.loads(kalender_channels_json)
except json.JSONDecodeError:
    raise ValueError("CHANNELS must be valid JSON")


# Validating GUILD_ID and MEMBER_ROLE_ID as integers
guild_id_str = os.getenv('GUILD_ID')
member_role_id_str = os.getenv('MEMBER_ROLE_ID')

if not guild_id_str or not guild_id_str.isdigit():
    raise ValueError("GUILD_ID must be a valid integer")
if not member_role_id_str or not member_role_id_str.isdigit():
    raise ValueError("MEMBER_ROLE_ID must be a valid integer")

guild_id = int(guild_id_str)
member_role_id = int(member_role_id_str)



event_reaction_emojis = ['✅', '🤔', '❌']


# ======================================
# ================ Bot =================
# ======================================


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


# Fetch user's server nickname
async def get_nickname(discord_user_id):
    guild = bot.get_guild(guild_id)
    if guild:
        member = guild.get_member(discord_user_id)
        if member:
            return member.nick or member.name  # Return nickname if available, fallback to name
    return None

# Check if the user has a specific role
async def is_club_member(discord_user_id: int):
    discord_user_id = int(discord_user_id)
    guild = bot.get_guild(guild_id)
    print(f"guild is {guild}")
    if guild:
        member = guild.get_member(discord_user_id)
        if discord_user_id is int:
            print("is int")
        print(f"member with id {discord_user_id} is {member}")
        if member:
            role = guild.get_role(member_role_id)  # Get the role by ID
            if role and role in member.roles:
                return True  # User has the role
    return False  # User does not have the role or is not a member


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





@bot.event
async def on_message(message):
    # Check if the message author is the bot itself; if so, return early
    if message.author != bot.user:
        return  # Skip processing if the message is from the bot itself

    # Check if the message was posted in one of the Kalenderchannels
    if message.channel.id in kalender_channels.values():
        

        # Create the buttons
        view = discord.ui.View()  # View holds all the interactive components
        view.add_item(discord.ui.Button(label="Ich bin dabei!", style=discord.ButtonStyle.success, custom_id="attend"))
        # view.add_item(discord.ui.Button(label="Nur vielleicht...", style=discord.ButtonStyle.success, custom_id="maybe"))
        view.add_item(discord.ui.Button(label="Ich kann nicht.", style=discord.ButtonStyle.primary, custom_id="not_attend"))



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



# TODO This entire thing needs to change if moving to gunicorn. It needs to access the api and run in its own container.
@bot.event
async def on_interaction(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    assert interaction
    assert interaction.guild

    # Get the Discord user ID
    discord_user_id = interaction.user.id

    # Fetch the latest nickname or default username
    nickname = await get_nickname(discord_user_id)

    # Check if the interaction is from a button
    if not interaction.type == discord.InteractionType.component:
        return
    
    # Get the message_id from the interaction
    assert interaction.message
    message_id = interaction.message.id
    user = interaction.user

    assert interaction.data
    custom_id = interaction.data.get('custom_id')

    action = None
    # Map the custom_id to an action
    if custom_id == "attend":
        action = "attend"
    elif custom_id == "not_attend":
        action = "not_attend"

    if not action:
        await interaction.followup.send("Unknown action.", ephemeral=True)
        return
    
    # Prepare data for the Flask API request
    data = {
        "discord_user_id": discord_user_id,
        "message_id": message_id,
        "action": action,
        "username": interaction.user.name
    }

    # Call the Flask API endpoint
    try:
        server_name = os.getenv('SERVER_NAME')
        response = requests.post(f"https://{server_name}/api/attendance", json=data)
        result = response.json()

        # Process the API response
        if response.status_code == 200:
            # await interaction.followup.send(result["message"], ephemeral=True)
            pass

        else:
            message = result.get('message', 'No message provided')
            print(f"Error from API: {message}")
            await interaction.followup.send(f"Failed to process your request: {message}", ephemeral=True)
            

    except Exception as e:
        await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)
        print(f"Error in handling interaction: {e}")





    
    # from flask import current_app as app
    # # from app import app
    # print("Got an Interaction")
    # with app.app_context():
    #     try:
    #         print(f"Message ID: {message_id}, Type: {type(message_id)}")
    #         event = Event.get_regular_events().filter_by(discord_post_id=message_id).first()
    #         if event:
    #             user = User.query.filter_by(discord_id=user.id).first()

    #             if not user:
    #                 # If the user doesn't exist in the DB, create a new one
    #                 user = User(discord_id=user.id, username=user.name) # type: ignore
    #                 db.session.add(user)
    #                 db.session.commit()
    #                 user = User.query.filter_by(discord_id=user.id).first()
                
    #             if action == "attend":
    #                 # Assuming you have an 'attendees' relationship on Event model
    #                 if user not in event.attendees:
    #                     event.attendees.append(user)
    #             elif action == "not_attend":
    #                 # Remove from the list of attendees
    #                 if user in event.attendees:
    #                     event.attendees.remove(user)

    #             db.session.commit()


    #             # Update the embed to reflect the new list of attendees
    #             assert interaction.channel
    #             updated_embed = generate_event_embed(event, interaction.channel.id, action='update')

    #             # Fetch the original message and update its embed
    #             if isinstance(interaction.channel, discord.TextChannel):
    #                 message = await interaction.channel.fetch_message(message_id)
    #                 await message.edit(embed=updated_embed)



    #             await interaction.followup.send(f"You have been marked as {action} for the event.", ephemeral=True)
    #         else:
    #             await interaction.followup.send("Event not found.", ephemeral=True)
    #     except Exception as e:
    #         db.session.rollback()  # Rollback any changes in case of error
    #         print(f"Error handling interaction: {e}")
    #         await interaction.followup.send("An error occurred while processing your request.", ephemeral=True)







# Function to start the bot
async def run_discord_bot():
    await bot.start(discord_token)  # Replace with your bot token