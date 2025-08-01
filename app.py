from flask import Flask
from flask_dance.contrib.discord import make_discord_blueprint, discord
import signal, os, asyncio, threading

import discord_bot
from services import *

from flask_compress import Compress

from tt_calendar.models import *
from tt_calendar.admin import init_admin
from tt_calendar.db_populate import check_and_populate_db

from flask_apscheduler import APScheduler

import logging

from dotenv import load_dotenv
load_dotenv()


# ======================================
# ============= TO DO LIST =============
# ======================================

# TODO Geschlossene Events nicht posten

# TODO Terminerinnerungen erste Name nicht als Liste

# TODO Template Einstellung korrekt gespeichert von wann posts live gehen?

# TODO debug doppelte Posts

# TODO Absagen tracken

# TODO Link zum Kalender präsenter machen

# TODO Veranstaltungen in Popup checken, nur 1 Woche wird getrackt

# TODO Checken, wann Nicknames gespeichert werden. Siehe Glauriel. Server nickname vs general.

# TODO show edit button in reservation popup only if posible to edit

# ? teilnehmen klicken im Kalender, sofern eingeloggt.

# TODO Event Form icon and such tags. Rename some HTML templates (head header into html_head)

# TODO Lageplan

# TODO Event overlay show event

# TODO Close Reqeust hat nur einen Mention.

# TODO Kategorien mit | o. ä. trennen und so im UI (event form) Unterkategorien erschaffen.
# Würde dann einfach an das originale Feld drangehängt werden. Geht rein über UI/JS.

# get overlapping events needs to also check virtual regulars.

# TODO Bekannte Collisionen bei Check Availability ausschließen.


# possible: Remove the DB logic from the api Calls and put them in their own module
# Mouse Cursor can_i_use checken und evtl ausblenden oder mit "move" ersetzen beim hovern über table_header

# Je nach GameCategory & Publicity in Event Form Discord Post Einstellung ausgrauen

# TODO nfc & qr zum scannen des tisches. 
# App sucht raus und lässt anwesend markieren oder neues event erstellen.
# TODO embed mit wochenevents in einem main channel?

# Feadback
# TODO Ersteller im Embed verlinken (mit @ und echtem Namen?)

# TODO event_forms POST - on failure resend arguments to re-fill form
# TODO event_forms Abbrechen Knopf, um zum gewählten Tag zurückzugelangen. (Back geht nicht immer, bei Post fehlern)

# TODO Favion & Titles of pages 

# TODO Vorlagen für Events mit Textbeschreibung.

# TODO Popup QR for ics

# TODO Löschantrag für eigene ID zu löschen.
# TODO DSGVO Datenabfrage?

# Feedback 10.4.2025

# Eigene Termine mit gesondertem Symbol oder Rahmen in der normalen Ansicht.

# Neu Laden auf dem Handy springt zu falschem Datum?

# ======================================
# ============= APP SETUP ==============
# ======================================
compress = Compress()

def create_app():
    app = Flask(__name__)
    compress.init_app(app)
    

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'  # Update the URI to your database
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False



    # ======================================
    # ============= Scheduling =============
    # ======================================

    scheduler = APScheduler()
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.start()

    from services.task_scheduler import register_scheduler_jobs
    register_scheduler_jobs(app, scheduler)
   
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

    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


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
    app.register_blueprint(blueprints.template_bp, url_prefix='/templates')
    app.register_blueprint(blueprints.cal, url_prefix='/calendar')
    app.register_blueprint(blueprints.ics, url_prefix='/ics')
    app.register_blueprint(blueprints.analytics_bp, url_prefix='/analytics')

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

    signal.signal(signal.SIGINT, signal_handler)

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, args=(app,))
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
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

