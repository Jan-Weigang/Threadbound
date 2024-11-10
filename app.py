from flask import Flask, redirect, url_for, session, request, jsonify, send_from_directory
from flask import render_template, request, redirect, url_for, flash, abort
from flask_dance.contrib.discord import make_discord_blueprint, discord
from datetime import datetime
import signal, os, asyncio, threading

import discord_bot
from services import *

from tt_calendar import decorators, utils
from tt_calendar.models import *
from tt_calendar.admin import init_admin
from tt_calendar.db_populate import check_and_populate_db


from dotenv import load_dotenv
load_dotenv()


# ======================================
# ============= TO DO LIST =============
# ======================================

# TODO Month into new htmx version

# TODO "1Personen" statt Namen in Popup. Check login requirements.

# TODO Remove the DB logic from the api Calls and put them in their own module

# TODO 3 Views: Day, Day with week and month. Selector in footer. All one dynamic site.




# TODO ICS Button in Discord view

# TODO Templates als Stammtsichkalender

# TODO Calendar / ICS integration?

# TODO Bottom nav and legends

# TODO Login-Loop bei nicht-Mitgliedern stoppen und erklären

# Fixed? kalender monat leitet nicht zu Tag auf Safari month.html 580


# TODO Buchformular beginnt scheinbar immer erst um 12 Uhr.

# TODO Mouse Cursor can_i_use checken und evtl ausblenden oder mit "move" ersetzen beim hovern über table_header
# TODO Ghost-Reservation für Stammtische, die durch attendees gefüllt wird? Dann einen Array, der sich merkt, welcher Tisch zuerst angeklickt wurde in JS und DB. So werden die Tische dann automatisch gefüllt. Aber das würde auch spezifische Capacities brauchen. Das ist mega umständlich
# TODO Attending als Nutzer über eine API-Route machen, die Nutzer mit Nicknamen erstellt, ohne, dass man member sein muss. Damit sich Gäste in DC mit eintragen können.
# TODO Reminder am Vortag oder Tag des events per pn.

# TODO Idee:
# TODO Stammtische schattiert einzeichnen, damit man Belegungen in der Tagesansicht sieht. 
# TODO Dann Stammtische immer wöchentlich einen Monat im Voraus erstellen und mit dem Template verlinken. Ist in der Woche ein Termin des Templates, wird es nicht angezeigt. 
# TODO Erstellt man einen Zukunftstermin, kann man den über Stammtische hinwegplanen und das Programm erstellt dann das Event und verlinkt den Stammtisch-Organisator. Der kann dann direkt in Discord zustimmen (sodass der Stammtisch in der Woche entfällt), oder ablehnen (womit das Event gelöscht wird). So könnte man größere Vereinsevents direkt zur Absprache führen und die drichtigen Personen per Chat zusammenbringen


# TODO Models anpassen mit "Template_ID" als Link, nullbar, default null.


# TODO Ab 4 Tischen automatische Planung und Vorstandsticket zur Bestätigung. Gilt als "Vereinsevent"
# TODO Diese Unterscheidung muss auch in die Module
# TODO Erinnerungs-PN

# TODO (1) Alembic - für Migration Changes und ICS Recurrence


# TODO auto archive old threads of events
# TODO nfc & qr zum scannen des tisches. App sucht raus und lässt anwesend markieren oder neues event erstellen.
# TODO spieltreff oder geschlossebe gruppen nicht auf discord packen oder optional machen
# TODO morgens um 9 eine erinnerung an event ersteller, ob stattfindet oder gelöscht werden soll. Normalfall: bleibt bestehen. Bei leuten, die seltener anwesend markieren und nicht kommen als ihre termine wahrnehmen dann auto-aktion löschung, wenn nicht bestätigt wird. Oder erinnerung optional..
# TODO embed mit wochenevents in einem main channel?
# TODO "editiert am" in mycalendar Popup rechts ausrichten (siehe Umbrechung bei engen Fenstern)
# TODO container-name für reservations nutzen
# TODO wifth vs minwidtj?

# Feadback
# TODO Ersteller im Embed verlinken (mit @ und echtem Namen?)
# TODO Abgesagte Events deutlicher markieren, indem das Logo ausgetauscht wird mit einem roten X

# TODO Wochentag in Tagesansicht anzeigen
# TODO Tagesansicht nicht erst ab 12 - Standard Ansicht ab 14 Uhr für Wochentage und 08 Uhr für Wochenende.
# TODO das sollte dann nochmal 1 Select field geben, in dem man die Startzeit anzeigen kann.
# TODO Dafür muss dann JS angepasst werden, damit die Arrays die korrekte Länge haben. In der Monatsansicht nur ab 12 ??

# TODO Month view should take an argument. Save in data- attribute and then take into loading.
# TODO Month view could use htmx but this would move the entire logic from js to python. Seems like work.

# TODO In event_forms Prüfen farbig hevorheben, dann grau, wenn geprüft. Reset on form change. 
# TODO In event_forms Nachricht über fail prüfung farbig hervorheben und "Gewählte Tische nicht verfügbar!" ändern
# TODO event_forms POST - on failure resend arguments to re-fill form
# TODO event_forms Abbrechen Knopf, um zum gewählten Tag zurückzugelangen. (Back geht nicht immer, bei Post fehlern)

# TODO Favion & Titles of pages 


# TODO Vorlagen für Events mit Textbeschreibung.

# TODO Popup QR for ics


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

import blueprints
app.register_blueprint(blueprints.api, url_prefix='/api')
app.register_blueprint(blueprints.event, url_prefix='/events')
app.register_blueprint(blueprints.cal, url_prefix='/calendar')
app.register_blueprint(blueprints.ics, url_prefix='/ics')

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
    session['is_member'] = discord_handler.is_role(user.discord_id, "member") # type: ignore
    session['is_mod'] = discord_handler.is_role(user.discord_id, "mod") # type: ignore
    session['is_admin'] = discord_handler.is_role(user.discord_id, "admin") # type: ignore

    print(f"I found user {user.username} with id {user.discord_id}. member: {session['is_member']} - mod: {session['is_mod']} - admin: {session['is_admin']}") # type: ignore

    if not session['is_member']:
        flash('You are not a member and cannot be given access', 'failure')
    return redirect(url_for('cal_bp.day'))  # Redirect to a member-specific area


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
    app.config['user_manager'] = user_manager

    event_manager = EventManager(discord_handler=discord_handler)
    app.config['event_manager'] = event_manager

    main_event_loop.run_until_complete(discord_bot.run_discord_bot())

