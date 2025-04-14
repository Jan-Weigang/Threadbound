from tt_calendar.models import Event, Reservation, Table, db
from tt_calendar.utils import date_range, localize_to_berlin_time, convert_to_utc
from datetime import datetime, timedelta
import pytz

def create_events_from_templates(weeks_ahead=8):
    today = datetime.now(pytz.utc).date()
    max_date = today + timedelta(weeks=weeks_ahead)

    templates = Event.get_template_events().all()
    generated_count = 0

    for template in templates:
        weekday = template.start_time.weekday()
        time_start = template.start_time.time()
        time_end = template.end_time.time()

        # Loop over upcoming days and match the template's weekday
        for day in date_range(today, max_date):
            if day.weekday() != weekday:
                continue

            # Construct datetime from this day + template times
            dt_start = localize_to_berlin_time(datetime.combine(day, time_start))
            dt_end = localize_to_berlin_time(datetime.combine(day, time_end))

            # Check if an event already exists for this template and day
            existing = Event.query.filter_by(template_id=template.id)\
                .filter(Event.start_time >= dt_start, Event.start_time < dt_end)\
                .first()
            if existing:
                continue

            # Clone the event
            new_event = Event(
                name=template.name,
                description=template.description,
                game_category_id=template.game_category_id,
                event_type_id=template.event_type_id,
                publicity_id=template.publicity_id,
                user_id=template.user_id,
                start_time=convert_to_utc(dt_start),
                end_time=convert_to_utc(dt_end),
                is_template=False,
                template_id=template.id
            )

            db.session.add(new_event)
            db.session.flush()  # Get the ID for the next step

            # Clone reservations
            for res in template.reservations:
                new_res = Reservation(
                    is_template=False,
                    user_id=res.user_id,
                    event_id=new_event.id,
                    table_id=res.table_id
                )
                db.session.add(new_res)

            generated_count += 1

    db.session.commit()
    return generated_count
