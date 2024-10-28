from flask import Flask, redirect, url_for, session, request, jsonify, send_from_directory
from flask import render_template, request, redirect, url_for, flash, abort
from flask_dance.contrib.discord import make_discord_blueprint, discord
from datetime import datetime
import signal, os, asyncio, threading

import discord_bot
from services import *

from tt_calendar import decorators, utils
from tt_calendar.models import db
from tt_calendar.api_routes import api
from tt_calendar.models import *
from tt_calendar.admin import init_admin
from tt_calendar.db_populate import check_and_populate_db


from dotenv import load_dotenv
load_dotenv()


# ======================================
# ============= TO DO LIST =============
# ======================================

# TODO =====================================
# TODO CHECK FOR SENSITIVE DATA AND GIT THIS!
# TODO =====================================

# TODO ICS Button in Discord view
# Link in discord


# TODO Icon to bottom unless container height too small @container to position relative
# TODO fix hover month out of current weekends

# TODO Templates als Stammtsichkalender

# TODO Calendar / ICS integration?

# TODO admin views better machen

# TODO Flask Flash as include

# TODO Bottom nav and legends

# TODO 
# Calendar Month Media:
# heat bar fixed width
# Event display nicht none

# TODO Login-Loop bei nicht-Mitgliedern stoppen und erklären

# TODO kalender monat leitet nicht zu Tag auf Safari month.html 580


# ======================================
# ============= APP SETUP ==============
# ======================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'  # Update the URI to your database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# ======================================
# ============= Open Auth ==============
# ======================================


# Set up Discord OAuth2
app.config['DISCORD_OAUTH_CLIENT_ID'] = os.getenv('CLIENT_ID') 
app.config['DISCORD_OAUTH_CLIENT_SECRET'] = os.getenv('CLIENT_SECRET') 
redirect_uri=os.getenv('REDIRECT_URI')
discord_blueprint = make_discord_blueprint(scope=['identify', 'email', 'guilds'])  # Adjust scopes based on your needs
app.register_blueprint(discord_blueprint, url_prefix='/login')


app.config['SERVER_NAME'] = os.getenv('SERVER_NAME')  # Replace with your actual domain or localhost for testing
app.config['APPLICATION_ROOT'] = '/'  # Set the application root
app.config['PREFERRED_URL_SCHEME'] = 'https'  # Use 'http' if you're testing locally


# ======================================
# ======== Database Populating =========
# ======================================

db.init_app(app)
init_admin(app)


# ======================================
# ============ Blueprints ==============
# ======================================

app.register_blueprint(api, url_prefix='/api')


# ======================================
# ============== Routes ================
# ======================================


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/')
def index():
    if not discord.authorized:
            return redirect(url_for('discord.login'))

    user = user_manager.get_or_create_user()
    is_member = discord_handler.is_member(discord_user_id=user.discord_id) # type: ignore
    session['is_club_member'] = is_member
    print(f"I found user {user} with id {user.discord_id} and member status: {is_member}") # type: ignore

    if not is_member:
        return redirect(url_for('discord.login'))  # Redirect to login if not a club member
    return redirect(url_for('mycalendar'))  # Redirect to a member-specific area


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        # Process form data to update each GameCategory's Discord channel
        for category_id, channel_id in request.form.items():
            game_category = db.session.get(GameCategory, category_id)
            if game_category and channel_id.isdigit():
                game_category.discord_channel_id = int(channel_id)
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))

    # Load data for GET request
    game_categories = GameCategory.query.all()
    discord_channels = DiscordChannel.query.all()
    return render_template('settings.html', game_categories=game_categories, discord_channels=discord_channels)


# ======================================
# ============ DB Routes ===============
# ======================================

@app.route('/thumbnail/<filename>')
def serve_thumbnail(filename):
    print(f"serving {filename}")
    return send_from_directory('static/images', filename)


@app.route('/events', methods=['GET'])
@decorators.login_required
def list_events():
    events = Event.get_regular_events().all()
    return render_template('events/list.html', events=events)


@app.route('/month', methods=['GET'])
def month():
    return render_template('month.html')


@app.route('/mycalendar', defaults={'view_type': 'regular'}, methods=['GET'])
@app.route('/mycalendar/<string:view_type>', methods=['GET'])
def mycalendar(view_type):
    if view_type not in ['public', 'regular', 'template']:
        abort(404)

    date = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))

    if view_type != 'public':
        if not discord.authorized:
            return redirect(url_for('mycalendar', view_type='public'))
    return render_template('mycalendar.html', view_type=view_type, date=date)


@app.route('/events/create', methods=['GET', 'POST'])
@decorators.login_required
def create_event():
    user = user_manager.get_or_create_user()

    if request.method == 'POST':
        form_data = utils.extract_form_data(request)
        if not form_data:
            return redirect(url_for('create_event'))

        # Check table availability
        available, conflicting_table = utils.check_availability(
            form_data['start_datetime'],
            form_data['end_datetime'],
            form_data['table_ids']
        )
        if not available:
            flash(f'Table {conflicting_table} is already reserved for the selected time.', 'error')
            return redirect(url_for('create_event'))

        # Create the event and reservations
        new_event = event_manager.create_event_in_db(user, form_data)

        event_date = form_data['start_datetime'].date().strftime('%Y-%m-%d')
        return redirect(url_for('mycalendar', date=event_date))


    # Get optional arguments from request
    requested_table_id = request.args.get('table_id')
    requested_start = request.args.get('time')
    requested_date = request.args.get('date')
    print(f"requested date is {requested_date}")
    
    requested_start_time, requested_end_time = utils.get_rounded_event_times(requested_start)

    print(f"optional arguments received: {requested_table_id} and {requested_start_time} and {requested_end_time}")
    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()
    tables = Table.query.all()
    return render_template('events/event_form.html', 
                           game_categories=game_categories, 
                           event_types=event_types, 
                           publicity_levels=publicity_levels, 
                           tables=tables,
                           table_id=requested_table_id,
                           start_time=requested_start_time,
                           end_time=requested_end_time,
                           requested_date=requested_date)


@app.route('/events/edit/<string:event_id>', methods=['GET', 'POST'])
@decorators.login_required
def edit_event(event_id):
    user = user_manager.get_or_create_user()
    event = Event.query.get_or_404(event_id)

    # Ensure the user is the creator of the event
    if event.user_id != user.id: # type:ignore
        flash('You are not authorized to edit this event.', 'error')
        return redirect(url_for('mycalendar'))  # Redirect to the event listing or another page

    print(f"event is {event} with date: {event.start_time}")
    tables = Table.query.all()


    if request.method == 'POST':
        form_data = utils.extract_form_data(request)
        if not form_data:
            return redirect(url_for('edit_event', event_id=event_id))
        
        # Check table availability except for already reserved by this event
        available, conflicting_table = utils.check_availability(
            form_data['start_datetime'],
            form_data['end_datetime'],
            form_data['table_ids'],
            exclude_event_id=event_id
        )
        if not available:
            flash(f'Table {conflicting_table} is already reserved for the selected time.', 'error')
            return redirect(url_for('edit_event', event_id=event_id))
        
        try:
            event_manager.update_event_in_db(event, user, form_data)
        except Exception as e:
            flash(f"An error occurred while updating the event: {e}", "danger")
            return redirect(url_for('edit_event', event_id=event.id))

        event_date = form_data['start_datetime'].date().strftime('%Y-%m-%d')
        return redirect(url_for('mycalendar', date=event_date))


    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()
    requested_start_time = event.start_time.strftime('%H:%M')
    requested_end_time = event.end_time.strftime('%H:%M')
    requested_date = event.start_time.date()
    return render_template('events/event_form.html', 
                           event=event, 
                           game_categories=game_categories, 
                           event_types=event_types, 
                           publicity_levels=publicity_levels,
                           tables=tables,
                           start_time=requested_start_time,
                           end_time=requested_end_time,
                           requested_date=requested_date)


@app.route('/events/delete/<string:event_id>', methods=['POST'])
@decorators.login_required
def delete_event(event_id):
    user = user_manager.get_or_create_user()
    event = Event.query.get_or_404(event_id)
    event_date = event.start_time.date().strftime('%Y-%m-%d')

    action = request.form.get('action', 'cancel')
    print(f"Action: {action}, Type: {type(action)}")

    # Ensure the user is the creator of the event
    if event.user_id != user.id: # type:ignore
        flash('You are not authorized to edit this event.', 'error')
        return redirect(url_for('mycalendar'))  # Redirect to the event listing or another page

    try:
        discord_handler.post_to_discord(event, action)
        # Delete the event
        db.session.delete(event)
        db.session.commit()  # Commit the deletion to the database
        return redirect(url_for('mycalendar', date=event_date))
    except Exception as e:
        # If there is an error, roll back the transaction
        db.session.rollback()
        flash(f"An error occurred while deleting the event: {e}", "danger")
        return redirect(url_for('edit_event', event_id=event_id))


# ======================================
# ============ Dev Server ==============
# ======================================


# Function to run Flask in a separate thread
def run_flask_app():
    app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False)

def signal_handler(signal, frame):
    print("Received signal, shutting down...")
    
    main_event_loop.call_soon_threadsafe(main_event_loop.stop)
    os._exit(0)


if __name__ == '__main__':
    with app.app_context():
        check_and_populate_db()
    signal.signal(signal.SIGINT, signal_handler)

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Run the Discord bot in the main asyncio event loop
    main_event_loop = asyncio.get_event_loop()

    # Create Class instances for Discord-Bot-Connection via main_event_loop
    discord_handler = DiscordHandler(main_event_loop=main_event_loop)
    app.config['discord_handler'] = discord_handler
    user_manager = UserManager(discord_handler=discord_handler, discord_api=discord)
    event_manager = EventManager(discord_handler=discord_handler)

    main_event_loop.run_until_complete(discord_bot.run_discord_bot())

