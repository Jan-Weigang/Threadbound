from tt_calendar.models import *
from tt_calendar import utils
import discord_bot

import asyncio
import datetime, pytz

# discord_handler.py
class DiscordHandler:
    def __init__(self, main_event_loop):
        assert main_event_loop is not None, "Main event loop must be provided"
        self.main_event_loop = main_event_loop


    def get_nickname(self, discord_id):
        future = asyncio.run_coroutine_threadsafe(
            discord_bot.get_nickname(discord_user_id=int(discord_id)),  # Call the async function to send a message
            self.main_event_loop
        )

        # Wait for the future to complete if you want to block until it's done (optional)
        try:
            nickname = future.result(timeout=2)  # waits 2s
            return nickname
        except Exception as e:
            return None 


    def is_role(self, discord_user_id, role_string):
        """
        Check if a user is a club member.
        """
        # Run the `is_club_member` coroutine in the main event loop
        future = asyncio.run_coroutine_threadsafe(
            discord_bot.is_guild_role(discord_user_id, role_string), 
            self.main_event_loop
        )

        try:
            # Wait for the result with a timeout
            return future.result(timeout=3)
        except Exception as e:
            print(f"Error checking membership: {e}")
            return None


    def post_to_discord(self, event, action='update'):
        channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
        if not channel_id:
            print("can't create post")
            return
        
        print(f"Trying to do discord handling with action {action}")

        if action == 'delete' and not utils.is_event_deletable(event):
                action = 'cancel'

        message_id = event.discord_post_id
        
        # Pick action and set coroutine
        if action == 'delete' and message_id:
            coroutine = discord_bot.delete_event_message_from_discord(channel_id, message_id)
        elif message_id:
            embed = discord_bot.generate_event_embed(event, channel_id, action)
            coroutine = discord_bot.update_event_embed_in_discord(channel_id, message_id=message_id, new_embed=embed)
        else:
            embed = discord_bot.generate_event_embed(event, channel_id, action)
            coroutine = discord_bot.post_event_embed_to_channel(channel_id, embed)

        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        # Wait for the future to complete if you want to block until it's done (optional)
        try:
            message_id = future.result(timeout=2)  # waits 2s
            return message_id
        except Exception as e:
            return None


    def send_reminders_in_threads(self, events):
        """
        Sends a reminder to each event's discussion thread by using its `discord_post_id`.
        """
        for event in events:
            message_id = event.discord_post_id
            creator_mention = f"<@{event.user.discord_id}>"  # Tag event creator
            
            if not message_id:
                print(f"⚠️ No Discord message ID found for event {event.id}. Skipping.")
                continue

            channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
            if not channel_id:
                print(f"⚠️ No Discord channel found for event {event.id}")
                return
            
            attendees = '\n - '.join([attendee.username for attendee in event.attendees])
            attendees = f"\n - {attendees}" if attendees else ""
            
            event_type = EventType.query.get(event.event_type_id)
            tables = Table.query.join(Reservation, Reservation.table_id == Table.id)\
                                        .filter(Reservation.event_id == event.id)\
                                        .all()
            tablesInfo = ', '.join(table.name for table in tables)
            
            print(f"Text: {creator_mention}, dein Event **{event.name}** beginnt heute um {event.start_time.strftime('%H:%M')}")
            reminder_text = f"""
📢 Reminder:

Deine Reservierung **{event.name}** *({tablesInfo})* beginnt heute um **{event.start_time.strftime('%H:%M')}**! 🎉
Eingetragen sind {len(event.attendees)} Personen: {attendees}


{creator_mention} bitte denke dran, das Event zu löschen und die Tische freizugebeben, sollte es ausfallen!"""

            # Get the thread from the original event message
            coroutine = discord_bot.send_message_in_event_thread(channel_id, message_id, reminder_text)
            future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

            try:
                future.result(timeout=2)
            except Exception as e:
                print(f"❌ Failed to send reminder for event {event.id}: {e}")


    def send_deletion_notice(self, event):
        """
        Sends a deletion notice event's discussion thread by using its `discord_post_id`.
        """
        message_id = event.discord_post_id
        creator_mention = f"<@{event.user.discord_id}>"  # Tag event creator
        
        if not message_id:
            print(f"⚠️ No Discord message ID found for event {event.id}. Skipping.")
            return

        channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
        if not channel_id:
            print(f"⚠️ No Discord channel found for event {event.id}")
            return
        
        
        print(f"Text: {creator_mention}, dein Event **{event.name}** wird gecancelt")
        reminder_text = f"""@everyone Die Reservierung **{event.name}** wurde **abgesagt**! 🎉"""

        # Get the thread from the original event message
        coroutine = discord_bot.send_message_in_event_thread(channel_id, message_id, reminder_text)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            future.result(timeout=2)
        except Exception as e:
            print(f"❌ Failed to send reminder for event {event.id}: {e}")


    # def create_private_channel(self, category_id, user1, user2, channel_name=None):
    #     """
    #     Creates a private channel in the given category and adds two users to it.

    #     Args:
    #         category_id (int): The ID of the Discord category where the channel will be created.
    #         user1 (User): The first user (User object from DB).
    #         user2 (User): The second user (User object from DB).
    #         channel_name (str, optional): The name of the channel. Defaults to "private-chat-<user1>-<user2>".

    #     Returns:
    #         int or None: The created channel ID, or None if an error occurred.
    #     """
    #     if not category_id or not user1 or not user2:
    #         print("Invalid input: Category ID and both users are required.")
    #         return None

    #     channel_name = channel_name or f"private-{user1.username}-{user2.username}"

    #     # Define permissions (private channel for only these users)
    #     permissions = {
    #         int(user1.discord_id): ["view_channel", "send_messages", "read_message_history"],
    #         int(user2.discord_id): ["view_channel", "send_messages", "read_message_history"]
    #     }

    #     # Call the bot function to create the channel
    #     coroutine = discord_bot.utils.create_private_channel(category_id, channel_name, permissions)
    #     future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

    #     try:
    #         channel_id = future.result(timeout=5)
    #         print(f"✅ Created private channel {channel_name} (ID: {channel_id})")
    #         return channel_id
    #     except Exception as e:
    #         print(f"❌ Failed to create private channel: {e}")
    #         return None
