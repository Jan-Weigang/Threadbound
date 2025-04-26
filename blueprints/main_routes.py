from flask import Blueprint, redirect, url_for, session, render_template, request, flash, send_from_directory, current_app
from flask_dance.contrib.discord import discord

from tt_calendar.models import db, Event, GameCategory, DiscordChannel, Reservation, EventType, Publicity
from tt_calendar import decorators
from tt_calendar import utils

from exceptions import *

import logging

main = Blueprint('main', __name__)

def get_user_manager():
    return current_app.config['user_manager']

def get_discord_handler():
    return current_app.config['discord_handler']


@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


@main.route('/login')
def login():
    if not discord.authorized:
            return redirect(url_for('discord.login'))

    user_manager = get_user_manager()
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))
    discord_handler = get_discord_handler()
    session['is_member'] = discord_handler.is_role(user.discord_id, "member") # type: ignore
    session['is_beirat'] = discord_handler.is_role(user.discord_id, "beirat") # type: ignore
    session['is_mod'] = discord_handler.is_role(user.discord_id, "mod") # type: ignore
    session['is_vorstand'] = discord_handler.is_role(user.discord_id, "vorstand") # type: ignore
    session['is_admin'] = discord_handler.is_role(user.discord_id, "admin") # type: ignore
    session['username'] = user.username
    session['user_id'] = user.id

    session.permanent = True

    logging.info(f"I logged in user {user.username} with id {user.discord_id}. member: {session['is_member']} - mod: {session['is_mod']} - admin: {session['is_admin']}") # type: ignore

    # if not session['is_member']:
    #     flash('You are not a member and cannot be given access', 'failure')
    return redirect(url_for('main.index'))  


@main.route('/')
def index():
    return redirect(url_for('cal_bp.view'))  # Redirect to a member-specific area


@main.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Process form data to update each GameCategory's Discord channel
        for category_id, channel_id in request.form.items():
            game_category = db.session.get(GameCategory, category_id)
            if game_category and channel_id.isdigit():
                game_category.discord_channel_id = int(channel_id)

        # Update EventType "should_not_post_to_discord"
        for etype in EventType.query.all():
            key = f"etype_block_{etype.id}"
            etype.should_not_post_to_discord = key in request.form

        # Update Publicity "should_not_post_to_discord"
        for publicity in Publicity.query.all():
            key = f"publicity_block_{publicity.id}"
            publicity.should_not_post_to_discord = key in request.form

        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('main.settings'))

    # Load data for GET
    game_categories = GameCategory.query.all()
    discord_channels = DiscordChannel.query.all()
    event_types = EventType.query.all()
    publicities = Publicity.query.all()

    return render_template(
        'settings.html',
        game_categories=game_categories,
        discord_channels=discord_channels,
        event_types=event_types,
        publicities=publicities
    )


# ======================================
# =========== Test routes ==============
# ======================================


@main.route('/remind')
def remind():
    import services.task_scheduler
    app = current_app._get_current_object()  # type: ignore
    services.task_scheduler.run_daily_reminder(app=app)
    return "Done"


# ======================================
# ============ DB Routes ===============
# ======================================

@main.route('/thumbnail/<filename>')
def serve_thumbnail(filename):
    logging.info(f"serving {filename}")
    return send_from_directory('static/images', filename)


@main.route('/events', methods=['GET'])
@decorators.login_required
def list_events():
    events = Event.get_regular_events().all()
    return render_template('events/list.html', events=events)