from tt_calendar.models import db, User, GameCategory, EventType, Publicity, Event, Table, Reservation, DiscordChannel

from sqlalchemy import or_, and_  # Import SQLAlchemy functions if needed
import discord
from flask import flash
from datetime import datetime, timedelta, date
import pytz

from dateutil.rrule import rrulestr

import logging


def check_availability(start_datetime, end_datetime, table_ids, exclude_event_id=None):
    """
    Check if the specified tables are available between the given start and end times, optionally excluding a specific event.

    Args:
    - start_datetime (datetime): The start time of the reservation.
    - end_datetime (datetime): The end time of the reservation.
    - table_ids (list): List of table IDs to check for availability.
    - exclude_event_id (int, optional): Event ID to exclude from the availability check.

    Returns:
    - (bool, int/None): Returns a tuple where the first element is True if available, False otherwise,
      and the second element is the conflicting table ID (or None if no conflict).
    """

    if start_datetime.tzinfo is None:
        start_datetime = localize_to_berlin_time(start_datetime)
    if end_datetime.tzinfo is None:
        end_datetime = localize_to_berlin_time(end_datetime)

    query = Event.get_regular_events().filter(
        Event.start_time < end_datetime,
        Event.end_time > start_datetime,
        Event.reservations.any(Reservation.table_id.in_(table_ids))
    )

    # Exclude a specific event ID from the check if provided
    if exclude_event_id:
        query = query.filter(Event.id != exclude_event_id)

    conflicting_event = query.first()
    if conflicting_event:
        # Find which table ID from the requested list is in conflict
        for table_id in table_ids:
            if any(reservation.table_id == table_id for reservation in conflicting_event.reservations):
                return False, table_id


    # 2. Check for future template occurrences that would conflict
    templates = Event.get_template_events().filter(
        Event.recurrence_rule.isnot(None),
        Event.reservations.any(Reservation.table_id.in_(table_ids))
    ).all()

    for template in templates:
        planned = get_planned_occurrences(template, start_datetime, end_datetime)
        if planned == []:
            return True, None
        
        excluded_dates = set((template.excluded_dates or "").splitlines())

        for occ in planned:
            if occ.date().isoformat() in excluded_dates:
                continue

            occ_start = occ
            occ_end = occ_start + template.duration

            # Check time overlap
            if occ_start < end_datetime and occ_end > start_datetime:
                for res in template.reservations:
                    if res.table_id in table_ids:
                        return False, res.table_id

    return True, None



def extract_event_form_data(request) -> dict | None:
    # Gather form data
    name = request.form['name']
    description = request.form['description']
    game_category_id = request.form['game_category_id']
    event_type_id = request.form['event_type_id']
    publicity_id = request.form['publicity_id']
    date = request.form['date']  # Date is in 'YYYY-MM-DD' format
    start_time = request.form['start_time']  # Start time in 'HH:MM' format
    end_time = request.form['end_time']  # End time in 'HH:MM' format
    table_ids_str = request.form['table_ids']
    table_ids = list(map(int, table_ids_str.split(',')))
    attend_self = request.form.get('attend_self') == 'on'
    discord_post_days_ahead = (
        int(request.form['discord_post_days_ahead'])
        if request.form.get('discord_post_days_ahead') else None
    )

    try:
        start_datetime = datetime.strptime(f"{date}T{start_time}", '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(f"{date}T{end_time}", '%Y-%m-%dT%H:%M')
    except ValueError:
        flash('Invalid date or time format. Please try again.', 'error')
        return None

    # Check that end time is after start time
    if end_datetime <= start_datetime:
        flash('End time must be after start time.', 'error')
        return None

    return {
        'name': name,
        'description': description,
        'game_category_id': game_category_id,
        'event_type_id': event_type_id,
        'publicity_id': publicity_id,
        'start_datetime': start_datetime,
        'end_datetime': end_datetime,
        'table_ids': table_ids,
        'attend_self': attend_self,
        'discord_post_days_ahead': discord_post_days_ahead
    }


def extract_template_form_data(request) -> dict | None:
    base_data = extract_event_form_data(request)
    if base_data is None:
        return None

    freq = request.form.get('frequency')
    interval = request.form.get('interval')
    rrule = None

    if freq == "WEEKLY":
        byday = request.form.get('byday')
        if byday:
            rrule = f"FREQ=WEEKLY;INTERVAL={interval};BYDAY={byday}"
    elif freq == "MONTHLY":
        bysetpos = request.form.get('bysetpos')
        byday_single = request.form.get('byday_single')
        if bysetpos and byday_single:
            rrule = f"FREQ=MONTHLY;BYSETPOS={bysetpos};BYDAY={byday_single}"

    base_data.update({
        'is_template': True,
        'recurrence_rule': rrule
    })
    return base_data




def get_rounded_event_times(requested_start) -> tuple[str, str]:
    logging.info(f"trying to get rounded event times with {requested_start}")
    # Round requested start time to nearest half hour and calculate end time
    if requested_start:
        requested_start_time = datetime.strptime(requested_start, "%H:%M")
        # Round to nearest half hour
        minute = requested_start_time.minute
        if minute < 15:
            rounded_minute = 0
        elif minute < 45:
            rounded_minute = 30
        else:
            rounded_minute = 0
            requested_start_time += timedelta(hours=1)
        requested_start_time = requested_start_time.replace(minute=rounded_minute, second=0, microsecond=0)
        requested_end_time = (requested_start_time + timedelta(hours=1)).strftime("%H:%M")
        requested_start_time = requested_start_time.strftime("%H:%M")
    else:
        requested_start_time = "17:00"
        requested_end_time = "19:00"

    return requested_start_time, requested_end_time




# ======================================
# =============== Events ===============
# ======================================

def is_event_deletable(event: Event) -> bool:
    # Get current time and calculate one month from now
    now = localize_to_berlin_time(datetime.now())
    one_month_from_now = now + timedelta(days=30)

    # Check if the event is within one month and has attendees
    if event.start_time <= one_month_from_now or len(event.attendees) > 1: # type: ignore
        return False
    return True


from zoneinfo import ZoneInfo
def get_planned_occurrences(template, start, end):
    """
    Returns a list of valid occurrences for a given template,
    filtered by excluded_dates.

    Assumes template.start_time is already aligned and tz-aware.
    """
    BERLIN = ZoneInfo("Europe/Berlin")

    if isinstance(start, date) and not isinstance(start, datetime):
        start = localize_to_berlin_time(datetime.combine(start, datetime.min.time()))

    if isinstance(end, date) and not isinstance(end, datetime):
        end = localize_to_berlin_time(datetime.combine(end, datetime.max.time()))
    try:
        dtstart_local = template.start_time.astimezone(BERLIN)
        rule = rrulestr(template.recurrence_rule, dtstart=dtstart_local)
        occurrences = rule.between(start, end, inc=False)

        excluded = set((template.excluded_dates or "").splitlines())
        return [occ for occ in occurrences if occ.date().isoformat() not in excluded]

    except Exception as e:
        import logging
        logging.warning(f"[RRULE] Invalid rule on template '{template.name}': {e}")
        return []



# ======================================
# ============== Datetime ==============
# ======================================


def convert_to_utc(berlin_time: datetime) -> datetime:
    # Assume berlin_time is a datetime object without timezone information
    berlin_zone = pytz.timezone('Europe/Berlin')
    localized_berlin_time = berlin_zone.localize(berlin_time, is_dst=None)
    utc_time = localized_berlin_time.astimezone(pytz.utc)
    return utc_time

def convert_to_berlin_time(utc_time: datetime) -> datetime:
    berlin_zone = pytz.timezone('Europe/Berlin')
    berlin_time = utc_time.astimezone(berlin_zone)
    return berlin_time

def localize_to_berlin_time(naive_time: datetime) -> datetime:
    berlin_zone = pytz.timezone('Europe/Berlin')
    localized_berlin_time = berlin_zone.localize(naive_time, is_dst=None)
    return localized_berlin_time

def to_berlin_midnight(date_str: str) -> datetime:
    naive = datetime.strptime(date_str, '%Y-%m-%d')
    berlin = pytz.timezone('Europe/Berlin')
    localized = berlin.localize(naive)
    return localized


def get_end_days_of_month(date):
    first_day_of_month = date.replace(day=1)
    last_day_of_month = (first_day_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    first_day_to_display = first_day_of_month - timedelta(days=(first_day_of_month.weekday()) % 7)
    last_day_to_display = last_day_of_month + timedelta(days=(13 - last_day_of_month.weekday()) % 7)
    first_day_to_display_str = first_day_to_display.strftime('%Y-%m-%d')
    last_day_to_display_str = last_day_to_display.strftime('%Y-%m-%d')
    return date_range(first_day_to_display, last_day_to_display), first_day_to_display_str, last_day_to_display_str

def date_range(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)

def get_end_days_of_week(date):
    week_start = date - timedelta(days=date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


# ======================================
# ============== Heat-Bar ==============
# ======================================

def get_heat_color(percentage):
    # Clamp the percentage between 0 and 1
    percentage = max(0, min(percentage, 1))

    # Lab color interpolation between lab(100% 60 -100) (green) and lab(55% 60 40) (red)
    lab_start = [100, 3, -9]  # Green
    lab_end = [0, 128, -85]   # Red

    last_five_percent = max(min(1, percentage * -20 + 19), 0)

    # Interpolate each component
    L = lab_start[0] + (lab_end[0] - lab_start[0]) * percentage
    a = lab_start[1] + (lab_end[1] - lab_start[1]) * min(max(0, percentage * 2 - 0.7), 1) * last_five_percent
    b = lab_start[2] + (lab_end[2] - lab_start[2]) * min(1, percentage * 2) * last_five_percent

    return f'lab({L:.1f}% {a:.1f} {b:.1f})'


def get_occupancy_by_day(reservation_data, tables):
    total_capacity = sum(table.capacity for table in tables)

    hours = 24

    # Create a dictionary to store hourly bookings for each day
    occupancy_by_day = {}

    # Iterate over each reservation
    for reservation in reservation_data:
        start_time = datetime.fromisoformat(reservation['start_time'])
        end_time = datetime.fromisoformat(reservation['end_time'])
        reservation_day = start_time.strftime('%Y-%m-%d')

        # Find the table by its table_id in the tables list
        table = next((t for t in tables if t.id == reservation['table_id']), None)

        # Ensure the table exists before proceeding
        if not table:
            logging.error(f"Table with ID {reservation['table_id']} not found.")
            continue  # Skip this reservation if the table is not found

        # Initialize hourly bookings for the day if not already present
        if reservation_day not in occupancy_by_day:
            occupancy_by_day[reservation_day] = [0] * hours  # One per hour

        for hour in range(max(0, start_time.hour), min(end_time.hour, hours - 1)):
            occupancy_by_day[reservation_day][hour] += table.capacity / total_capacity

    return occupancy_by_day
