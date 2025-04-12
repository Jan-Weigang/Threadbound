from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime
from tt_calendar.models import Event
import logging
from flask import current_app

logging.basicConfig(level=logging.INFO)

def run_daily_reminder():
    app = current_app._get_current_object() #type: ignore
    with app.app_context:
        """Fetch events for today and send reminders to Discord."""
        berlin_tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(berlin_tz)
        
        # Get the start and end of today
        start_of_day = berlin_tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
        end_of_day = berlin_tz.localize(datetime(now.year, now.month, now.day, 23, 59, 59))

        print(f"Running Event Remeinder for today: {start_of_day} to {end_of_day}")

        with current_app.app_context():
            events = Event.get_regular_events().filter(
                Event.start_time >= start_of_day.astimezone(pytz.utc),  # Convert to UTC for DB
                Event.start_time <= end_of_day.astimezone(pytz.utc)  # Convert to UTC for DB
            ).all()

            if not events:
                logging.info(f"📅 No events today ({now.strftime('%Y-%m-%d')}). Skipping reminder.")
                return

            logging.info(f"📢 Sending reminders for {len(events)} events.")
            discord_handler = current_app.config['discord_handler']
            discord_handler.send_reminders_in_threads(events)

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_daily_reminder,
    trigger=CronTrigger(hour=9, minute=0, timezone=pytz.timezone('Europe/Berlin')),
    id="daily_reminder",
    replace_existing=True
)
