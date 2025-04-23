from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tt_calendar.models import Event, Reservation, Table, db
from tt_calendar import utils

import pytz
from datetime import date, datetime, timedelta

from dateutil.rrule import rrulestr


import logging
from flask import current_app

logging.basicConfig(level=logging.INFO)

def run_daily_reminder(app):
    logging.info("🔔 Running daily reminder job...")

    with app.app_context():
        """Fetch events for today and send reminders to Discord."""
        berlin_tz = pytz.timezone('Europe/Berlin')
        now = datetime.now(berlin_tz)
        
        # Get the start and end of today
        start_of_day = berlin_tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
        end_of_day = berlin_tz.localize(datetime(now.year, now.month, now.day, 23, 59, 59))

        logging.info(f"Running Event Remeinder for today: {start_of_day} to {end_of_day}")

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


def create_events_from_templates(start_date: date | None = None, end_date: date | None = None, conflict_check_needed: bool = True, app = None) -> int:
    """
    Create real event instances from templates within a date range.
    If no range is provided, it defaults to today until 8 weeks ahead.
    These events automatically get approved for size.
    """
    logging.info("♻️ Running recurring event generation...")
    if not app:
        app = current_app._get_current_object() #type: ignore

    with app.app_context():
        today = utils.localize_to_berlin_time(datetime.now()).date()
        start_date = start_date or today
        end_date = end_date or (today + timedelta(weeks=4))

        templates = Event.get_template_events().all()
        event_manager = app.config['event_manager']
        created_count = 0

        for template in templates:
            table_ids = [r.table_id for r in template.reservations]
            user = template.user

            if template.recurrence_rule:
                # 🔁 Use RRULE
                planned = utils.get_planned_occurrences(template, start_date, end_date)
            else:
                pass

            excluded_dates = set((template.excluded_dates or "").splitlines())

            for occ in planned:
                if occ.date().isoformat() in excluded_dates:
                    continue

                dt_start = occ
                dt_end = dt_start + template.duration
                start_utc = dt_start
                end_utc = dt_end

                exists = Event.get_regular_events().filter_by(template_id=template.id).filter(
                    Event.start_time == start_utc
                ).first()

                if exists:
                    continue

                if conflict_check_needed:
                    # ✅ Conflict check
                    available, conflict_table = utils.check_availability(start_utc, end_utc, table_ids)
                    if not available:
                        logging.info(f"⛔ Skipping {start_utc} from template {template.id} — table {conflict_table} unavailable.")
                        # event_manager.exclude_date_from_template(template, dt_start.date())
                        # TODO This might not be that great an idea..
                        continue
                
                from tt_calendar.models import EventState
                new_event = event_manager.create_event_in_db(
                    user=user,
                    name=template.name,
                    description=template.description,
                    game_category_id=template.game_category_id,
                    event_type_id=template.event_type_id,
                    publicity_id=template.publicity_id,
                    start_time=start_utc,
                    end_time=end_utc,
                    table_ids=table_ids,
                    template_id=template.id,
                    state_size=EventState.APPROVED
                )

                event_manager.exclude_date_from_template(template, dt_start.date())

                created_count += 1

        db.session.commit()
        logging.info(f"✅ Generated {created_count} new events from templates.")
        return created_count


def register_scheduler_jobs(app, scheduler):
    scheduler.add_job(
        func=lambda: run_daily_reminder(app=app),
        trigger=CronTrigger(hour=9, minute=0, timezone=pytz.timezone('Europe/Berlin')),
        id="daily_reminder",
        replace_existing=True
    )

    from services.task_scheduler import create_events_from_templates
    scheduler.add_job(
        func=lambda: create_events_from_templates(app=app),
        trigger=CronTrigger(hour=8, minute=0, timezone=pytz.timezone('Europe/Berlin')),
        id="generating_recurring_events",
        replace_existing=True
    )