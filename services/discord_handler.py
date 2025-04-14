from tt_calendar.models import *
from tt_calendar import utils
import discord_bot
from discord_bot.ticketing import create_ticket, change_resolved_ticket_view  # adjust path as needed

import asyncio
import datetime, pytz
import logging

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
            import traceback
            logging.error(f"Error checking membership: {e}")
            traceback.print_exc()
            return None


    def post_to_discord(self, event, action='update'):
        channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
        if not channel_id:
            logging.info("can't create post")
            return
        
        logging.info(f"discord handling with action {action}")
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
                logging.info(f"⚠️ No Discord message ID found for event {event.id}. Skipping.")
                continue

            channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
            if not channel_id:
                logging.info(f"⚠️ No Discord channel found for event {event.id}")
                return
            
            attendees = '\n - '.join([attendee.username for attendee in event.attendees])
            attendees = f"\n - {attendees}" if attendees else ""
            
            event_type = EventType.query.get(event.event_type_id)
            tables = Table.query.join(Reservation, Reservation.table_id == Table.id)\
                                        .filter(Reservation.event_id == event.id)\
                                        .all()
            tablesInfo = ', '.join(table.name for table in tables)
            
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
                logging.error(f"❌ Failed to send reminder for event {event.id}: {e}")


    def send_deletion_notice(self, event):
        """
        Sends a deletion notice event's discussion thread by using its `discord_post_id`.
        """
        message_id = event.discord_post_id
        creator_mention = f"<@{event.user.discord_id}>"  # Tag event creator
        
        if not message_id:
            logging.info(f"⚠️ No Discord message ID found for event {event.id}. Skipping.")
            return

        channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None
        if not channel_id:
            logging.info(f"⚠️ No Discord channel found for event {event.id}")
            return
        
        reminder_text = f"""@everyone Die Reservierung **{event.name}** wurde **abgesagt**! 🎉"""

        # Get the thread from the original event message
        coroutine = discord_bot.send_message_in_event_thread(channel_id, message_id, reminder_text)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            future.result(timeout=2)
        except Exception as e:
            logging.error(f"❌ Failed to send reminder for event {event.id}: {e}")


    def add_user_to_event_thread(self, event, user_discord_id: int):
        """
        Adds a user to the Discord thread associated with the event.
        """
        message_id = event.discord_post_id
        channel_id = event.game_category.channel.discord_channel_id if event.game_category and event.game_category.channel else None

        if not message_id:
            logging.info(f"⚠️ No Discord message ID found for event {event.id}. Skipping.")
            return

        if not channel_id:
            logging.info(f"⚠️ No Discord channel found for event {event.id}")
            return

        coroutine = discord_bot.add_user_to_event_thread(channel_id, message_id, user_discord_id)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            future.result(timeout=2)
        except Exception as e:
            logging.error(f"❌ Failed to add user {user_discord_id} to event thread {event.id}: {e}")


    def open_ticket_for_overlap(self, creator_id: int, overlapped_user_id: int, new_event=None, existing_event=None):
        """
        Creates a Discord ticket for overlapping events between two users.
        """
        coroutine = create_ticket(bot=discord_bot.bot, creator_id=creator_id, overlapped_member_id=overlapped_user_id,
                new_event=new_event, existing_event=existing_event)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            channel_id = future.result(timeout=3)
            return channel_id
        except Exception as e:
            logging.error(f"❌ Failed to create overlap ticket for {creator_id=} {overlapped_user_id=}: {e}")
            return None


    def open_ticket_for_size(self, creator_id: int):
        """
        Creates a Discord ticket for overlapping events between two users.
        """
        coroutine = create_ticket(bot=discord_bot.bot, creator_id=creator_id)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            channel_id = future.result(timeout=3)
            return channel_id
        except Exception as e:
            logging.error(f"❌ Failed to create size ticket for {creator_id=}: {e}")
            return None
        

    def resolve_size_ticket_channel(self, event):
        """
        Replaces the first message's view in a ticket channel with just a close button.
        """
        channel_id = event.size_request_discord_channel_id
        coroutine = change_resolved_ticket_view(bot=discord_bot.bot, channel_id=channel_id)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            future.result(timeout=3)
        except Exception as e:
            import traceback
            logging.error(f"❌ Failed to replace view in channel {channel_id}: {e}")
            traceback.print_exc()


    def resolve_overlap_ticket_channel(self, overlap):
        """
        Replaces the first message's view in a ticket channel with just a close button.
        """
        channel_id = overlap.request_discord_channel_id
        coroutine = change_resolved_ticket_view(bot=discord_bot.bot, channel_id=channel_id)
        future = asyncio.run_coroutine_threadsafe(coroutine, self.main_event_loop)

        try:
            future.result(timeout=5)
        except Exception as e:
            logging.error(f"❌ Failed to replace view in channel {channel_id}: {e}")
