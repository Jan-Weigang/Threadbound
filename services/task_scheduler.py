from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tt_calendar.models import Event, Reservation, Table, db
from tt_calendar import utils

import pytz
from datetime import datetime, timedelta

from dateutil.rrule import rrulestr


import logging
from flask import current_app

logging.basicConfig(level=logging.INFO)

def run_daily_reminder():
    logging.info("🔔 Running daily reminder job...")

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


def create_events_from_templates(weeks_ahead: int = 8) -> int:
    logging.info("♻️ Running recurring event generation...")
    app = current_app._get_current_object()     # type: ignore

    with app.app_context():
        today = utils.localize_to_berlin_time(datetime.now()).date()
        max_date = today + timedelta(weeks=weeks_ahead)

        templates = Event.get_template_events().all()
        event_manager = app.config['event_manager']
        created_count = 0

        for template in templates:
            table_ids = [r.table_id for r in template.reservations]
            user = template.user
            duration = template.end_time - template.start_time
            local_start = utils.convert_to_berlin_time(template.start_time)

            if template.recurrence_rule:
                # 🔁 Use RRULE
                try:
                    rule = rrulestr(template.recurrence_rule, dtstart=local_start)
                    occurrences = rule.between(
                        utils.localize_to_berlin_time(datetime.combine(today, datetime.min.time())),
                        utils.localize_to_berlin_time(datetime.combine(max_date, datetime.max.time())),
                        inc=True
                    )
                except Exception as e:
                    logging.warning(f"Invalid RRULE for template {template.id}: {e}")
                    continue
            else:
                pass

            excluded_dates = set((template.excluded_dates or "").splitlines())

            for occ in occurrences:
                if occ.date().isoformat() in excluded_dates:
                    continue

                dt_start = utils.localize_to_berlin_time(occ)
                dt_end = dt_start + duration
                start_utc = utils.convert_to_utc(dt_start)
                end_utc = utils.convert_to_utc(dt_end)

                exists = Event.get_regular_events().filter_by(template_id=template.id).filter(
                    Event.start_time == start_utc
                ).first()

                if exists:
                    continue

                # ✅ Conflict check
                available, conflict_table = utils.check_availability(start_utc, end_utc, table_ids)
                if not available:
                    logging.info(f"⛔ Skipping {start_utc} from template {template.id} — table {conflict_table} unavailable.")
                    continue

                event_manager.create_event_in_db(
                    user=user,
                    name=template.name,
                    description=template.description,
                    game_category_id=template.game_category_id,
                    event_type_id=template.event_type_id,
                    publicity_id=template.publicity_id,
                    start_time=start_utc,
                    end_time=end_utc,
                    table_ids=table_ids,
                    template_id=template.id
                )

                event_manager.exclude_date_from_template(template, dt_start.date())

                created_count += 1

        logging.info(f"✅ Generated {created_count} new events from templates.")
        return created_count

        






# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=run_daily_reminder,
    trigger=CronTrigger(hour=9, minute=0, timezone=pytz.timezone('Europe/Berlin')),
    id="daily_reminder",
    replace_existing=True
)
scheduler.add_job(
    func=create_events_from_templates,
    trigger=CronTrigger(hour=8, minute=0, timezone=pytz.timezone('Europe/Berlin')),
    id="generating_recurring_events",
    replace_existing=True
)