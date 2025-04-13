from flask import Flask
from flask_dance.contrib.discord import make_discord_blueprint, discord
from datetime import datetime
import signal, os, asyncio, threading

import discord_bot
from services import *
from services.task_scheduler import scheduler


from tt_calendar.models import *
from tt_calendar.admin import init_admin
from tt_calendar.db_populate import check_and_populate_db


from dotenv import load_dotenv
load_dotenv()


# ======================================
# ============= TO DO LIST =============
# ======================================

# api/resolve_overlap 404 error?

# Abgesagt ignorieren wenn gelöscht oder nicht published

# in tickets infos des events

# ? teilnehmen klicken im Kalender, sofern eingeloggt.

# TODO make templates visible in calendar.

# possible: Remove the DB logic from the api Calls and put them in their own module
# Possibly add other hovering buttons for time scale movements (left right)

# TODO Templates als Stammtsichkalender
# Mouse Cursor can_i_use checken und evtl ausblenden oder mit "move" ersetzen beim hovern über table_header
# Ghost-Reservation für Stammtische, die durch attendees gefüllt wird? Dann einen Array, der sich merkt, welcher Tisch zuerst angeklickt wurde in JS und DB. So werden die Tische dann automatisch gefüllt. Aber das würde auch spezifische Capacities brauchen. Das ist mega umständlich

# DONE? Attending als Nutzer über eine API-Route machen, die Nutzer mit Nicknamen erstellt, ohne, dass man member sein muss. Damit sich Gäste in DC mit eintragen können.
# Reminder am Vortag oder Tag des events per pn.

# TODO Idee:
# TODO Stammtische schattiert einzeichnen, damit man Belegungen in der Tagesansicht sieht. 
# TODO Dann Stammtische immer wöchentlich einen Monat im Voraus erstellen und mit dem Template verlinken. Ist in der Woche ein Termin des Templates, wird es nicht angezeigt. 
# TODO Erstellt man einen Zukunftstermin, kann man den über Stammtische hinwegplanen und das Programm erstellt dann das Event und verlinkt den Stammtisch-Organisator. Der kann dann direkt in Discord zustimmen (sodass der Stammtisch in der Woche entfällt), oder ablehnen (womit das Event gelöscht wird). So könnte man größere Vereinsevents direkt zur Absprache führen und die drichtigen Personen per Chat zusammenbringen

# TODO Models anpassen mit "Template_ID" als Link, nullbar, default null.


# TODO (1) Alembic - für Migration Changes und ICS Recurrence


# TODO auto archive old threads of events
# TODO nfc & qr zum scannen des tisches. App sucht raus und lässt anwesend markieren oder neues event erstellen.
# TODO spieltreff oder geschlossebe gruppen nicht auf discord packen oder optional machen
# TODO morgens um 9 eine erinnerung an event ersteller, ob stattfindet oder gelöscht werden soll. Normalfall: bleibt bestehen. Bei leuten, die seltener anwesend markieren und nicht kommen als ihre termine wahrnehmen dann auto-aktion löschung, wenn nicht bestätigt wird. Oder erinnerung optional..
# TODO embed mit wochenevents in einem main channel?
# TODO container-name für reservations nutzen

# Feadback
# TODO Ersteller im Embed verlinken (mit @ und echtem Namen?)
# TODO Abgesagte Events deutlicher markieren, indem das Logo ausgetauscht wird mit einem roten X

# TODO Wochentag in Tagesansicht anzeigen

# TODO In event_forms Prüfen farbig hevorheben, dann grau, wenn geprüft. Reset on form change. 
# TODO In event_forms Nachricht über fail prüfung farbig hervorheben und "Gewählte Tische nicht verfügbar!" ändern
# TODO event_forms POST - on failure resend arguments to re-fill form
# TODO event_forms Abbrechen Knopf, um zum gewählten Tag zurückzugelangen. (Back geht nicht immer, bei Post fehlern)

# TODO Favion & Titles of pages 

# TODO Vorlagen für Events mit Textbeschreibung.

# TODO Popup QR for ics

# TODO Konflikte als Channels in Discord, Konfliktmarker als Merker für Änderungen

# TODO Stammtischleiter in DB / Beiräte

# TODO Löschantrag für eigene ID zu löschen.
# TODO DSGVO Datenabfrage?

# Feedback 10.4.2025

# Bei Event erstellung (Ansicht) eine Checkbox für teilnehmen, die standardmäßig an ist?

# Bei Editieren eine falsche Anzeige? Rollenspiel aber mit BrettspielwürfeL?
# Eigene Termine mit gesondertem Symbol oder Rahmen in der normalen Ansicht.
# "Heute" farbig hervorheben.
# Fehlende Berechtigungen zum Löschen des 3TH Kalender Bots
# Admins können noch nicht editieren, events

# Neu Laden auf dem Handy springt zu falschem Datum?
# für Termine in Vergangenheit keine Threads!

# ======================================
# ============= APP SETUP ==============
# ======================================
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'  # Update the URI to your database
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    # ======================================
    # ============= Open Auth ==============
    # ======================================


    # Set up Discord OAuth2
    app.config['DISCORD_OAUTH_CLIENT_ID'] = os.getenv('CLIENT_ID') 
    app.config['DISCORD_OAUTH_CLIENT_SECRET'] = os.getenv('CLIENT_SECRET') 
    redirect_uri=os.getenv('REDIRECT_URI')
    discord_blueprint = make_discord_blueprint(
        scope=['identify', 'email', 'guilds'],
        redirect_to="main.login")  # Adjust scopes based on your needs
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
    app.register_blueprint(blueprints.main)
    app.register_blueprint(blueprints.api, url_prefix='/api')
    app.register_blueprint(blueprints.event_bp, url_prefix='/events')
    app.register_blueprint(blueprints.cal, url_prefix='/calendar')
    app.register_blueprint(blueprints.ics, url_prefix='/ics')

    return app



# ======================================
# ============ Dev Server ==============
# ======================================


# Function to run Flask in a separate thread
def run_flask_app(app):
    app.run(host='0.0.0.0', port=5000, use_reloader=False, debug=False)

def signal_handler(signal, frame):
    print("Received signal, shutting down...")
    
    main_event_loop.call_soon_threadsafe(main_event_loop.stop)
    os._exit(0)


if __name__ == '__main__':
    app = create_app()


    with app.app_context():
        check_and_populate_db()
        scheduler.start()
    signal.signal(signal.SIGINT, signal_handler)

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, args=(app,))
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

    assert discord_bot
    main_event_loop.run_until_complete(discord_bot.run_discord_bot())

