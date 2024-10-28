from tt_calendar.models import db, User, GameCategory, EventType, Publicity, Event, Table, Reservation, DiscordChannel

from sqlalchemy import or_, and_  # Import SQLAlchemy functions if needed
import discord
from flask import flash
from datetime import datetime, timedelta
import pytz


# def check_availability(start_datetime, end_datetime, table_ids):
#     """
#     Check if the specified tables are available between the given start and end time.

#     Args:
#     - start_datetime (datetime): The start time of the reservation.
#     - end_datetime (datetime): The end time of the reservation.
#     - table_ids (list): List of table IDs to check for availability.

#     Returns:
#     - (bool, int/None): Returns a tuple where the first element is True if available, False otherwise,
#       and the second element is the conflicting table ID (or None if no conflict).
#     """
#     for table_id in table_ids:
#         reservation_check = Event.query.filter(
#             Event.start_time < end_datetime,
#             Event.end_time > start_datetime,
#             Event.reservations.any(Reservation.table_id == table_id)
#         ).first()
#         if reservation_check:
#             return False, table_id
#     return True, None

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

    start_datetime = localize_to_berlin_time(start_datetime)
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

    return True, None


# def generate_event_message(event) -> str:
#     message = (
#         f"📅 **Event:** {event.name}\n"
#         f"📝 **Description:** {event.description or 'No description provided'}\n"
#         f"🎮 **Category:** {event.game_category.name}\n"
#         f"🔖 **Type:** {event.event_type.name}\n"
#         f"🕒 **Starts:** {event.start_time.strftime('%Y-%m-%d %H:%M')}\n"
#         f"🕓 **Ends:** {event.end_time.strftime('%Y-%m-%d %H:%M')}\n"
#         f"👤 **Organized by:** {event.user.username}\n"
#         f"💬 **Publicity:** {event.publicity.name}\n"
#         f"💺 **Reservations:** {', '.join([reservation.table.name for reservation in event.reservations]) or 'No tables reserved yet.'}\n"
#     )
#     return message



def extract_form_data(request) -> dict | None:
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
        'table_ids': table_ids
    }



def get_rounded_event_times(requested_start) -> tuple[str, str]:
    print(f"trying to get rounded event times with {requested_start}")
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
    if event.start_time <= one_month_from_now or event.attendees.count() > 0:
        return False
    return True



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