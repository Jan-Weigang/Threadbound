from flask import Blueprint, redirect, url_for, session, render_template, request, flash, send_from_directory, current_app
from flask_dance.contrib.discord import discord

from tt_calendar.models import db, Event, GameCategory, DiscordChannel, Reservation
from tt_calendar import decorators
from tt_calendar import utils

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
    user = user_manager.get_or_create_user()
    discord_handler = get_discord_handler()
    session['is_member'] = discord_handler.is_role(user.discord_id, "member") # type: ignore
    session['is_beirat'] = discord_handler.is_role(user.discord_id, "beirat") # type: ignore
    session['is_mod'] = discord_handler.is_role(user.discord_id, "mod") # type: ignore
    session['is_vorstand'] = discord_handler.is_role(user.discord_id, "vorstand") # type: ignore
    session['is_admin'] = discord_handler.is_role(user.discord_id, "admin") # type: ignore
    session['username'] = user.username

    session.permanent = True

    print(f"I found user {user.username} with id {user.discord_id}. member: {session['is_member']} - mod: {session['is_mod']} - admin: {session['is_admin']}") # type: ignore

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
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('main.settings'))

    # Load data for GET request
    game_categories = GameCategory.query.all()
    discord_channels = DiscordChannel.query.all()
    return render_template('settings.html', game_categories=game_categories, discord_channels=discord_channels)


# ======================================
# =========== Test routes ==============
# ======================================


@main.route('/remind')
def remind():
    import services.task_scheduler
    app = current_app._get_current_object()  # type: ignore
    services.task_scheduler.run_daily_reminder(app=app)
    return "Done"

@main.route('/query')
def myquery():
    tests = Event.get_regular_events() # type: ignore
    print("Getting events by query")
    for test in tests:
        print(test)

    print("getting events with filter")

    tests = Event.query.filter(Event.deleted==False).all()
    for test in tests:
        print(test)

    
    return "Done"


# ======================================
# ============ DB Routes ===============
# ======================================

@main.route('/thumbnail/<filename>')
def serve_thumbnail(filename):
    print(f"serving {filename}")
    return send_from_directory('static/images', filename)


@main.route('/events', methods=['GET'])
@decorators.login_required
def list_events():
    events = Event.get_regular_events().all()
    return render_template('events/list.html', events=events)