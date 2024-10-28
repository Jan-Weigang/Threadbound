from tt_calendar.models import *
from tt_calendar import utils
import discord_bot

import asyncio

# discord_handler.py
class DiscordHandler:
    def __init__(self, main_event_loop):
        assert main_event_loop is not None, "Main event loop must be provided"
        self.main_event_loop = main_event_loop


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
