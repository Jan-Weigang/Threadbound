from flask import request, Blueprint, abort, send_file
from tt_calendar.models import *

from ics import Calendar, Event as ICSEvent
from io import BytesIO
import pytz

ics = Blueprint('ics_bp', __name__)

# HELPER FUNCTIONS

def create_ics_event_from_event(event):
    ics_event = ICSEvent()
    ics_event.name = event.name
    ics_event.begin = event.start_time
    ics_event.end = event.end_time
    ics_event.uid = f"{event.id}@3TH"
    ics_event.description = event.description
    if event.get_discord_message_url():
        ics_event.location = f"https://{event.get_discord_message_url()}"
    ics_event.created = event.time_created
    return ics_event

# ROUTES

@ics.route('/event/<string:event_id>', methods=['GET'])
def get_event_ics(event_id):
    # Fetch event by ID
    given_event = Event.query.get(event_id)
    if not given_event or given_event.deleted:
        abort(404, description="Event not found")

    calendar = Calendar()

    # Determine if the event is part of a recurring series
    if given_event.template_id:
        events = Event.get_events_linked_to_template(given_event.template_id).order_by(Event.start_time).all()
    else:
        events = [given_event]


    for event in events:
        calendar.events.add(create_ics_event_from_event(event))

    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))

    response = send_file(calendar_bytes, as_attachment=True, download_name=f"{given_event.name}.ics", mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename="{given_event.name}.ics"'
    return response


@ics.route('/calendar/all', methods=['GET'])
def get_all_events_ics():
    calendar = Calendar()

    events = Event.get_regular_events().order_by(Event.start_time).all()
    for event in events:
        calendar.events.add(create_ics_event_from_event(event))

    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))
    return send_file(calendar_bytes, as_attachment=True, download_name="calendar_all.ics", mimetype='text/calendar')


@ics.route('/calendar/public', methods=['GET'])
def get_public_events_ics():
    calendar = Calendar()

    public_events = Event.get_regular_events().filter(Event.publicity_id == 1).order_by(Event.start_time).all()
    for event in public_events:
        calendar.events.add(create_ics_event_from_event(event))

    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))
    return send_file(calendar_bytes, as_attachment=True, download_name="calendar_public.ics", mimetype='text/calendar')


@ics.route('/calendar/gamecategory/<int:gamecategory_id>', methods=['GET'])
def get_gamecategory_events_ics(gamecategory_id):
    calendar = Calendar()

    events = Event.get_regular_events() \
        .filter(Event.game_category_id == gamecategory_id) \
        .order_by(Event.start_time).all()

    for event in events:
        calendar.events.add(create_ics_event_from_event(event))

    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))
    return send_file(calendar_bytes, as_attachment=True, download_name=f"calendar_gamecategory_{gamecategory_id}.ics", mimetype='text/calendar')
