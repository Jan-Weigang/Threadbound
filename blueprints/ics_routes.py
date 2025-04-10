from flask import request, Blueprint, abort, send_file
from tt_calendar.models import *

from ics import Calendar, Event as ICSEvent
from io import BytesIO
import pytz

ics = Blueprint('ics_bp', __name__)

@ics.route('/event/<string:event_id>', methods=['GET'])
def get_event_ics(event_id):
    # Fetch event by ID
    event = Event.query.get(event_id)
    if not event:
        abort(404, description="Event not found")

    calendar = Calendar()

    # Determine if the event is part of a recurring series
    if event.template_id:
        # Fetch all future events linked to the same template_id
        instances = Event.query.filter(
            Event.template_id == event.template_id
        ).order_by(Event.start_time).all()
    else:
        # Single event, not part of a recurring series
        instances = [event]


    ics_event = ICSEvent()
    
    for instance in instances:
        ics_event.name = instance.name
        ics_event.begin = instance.start_time
        ics_event.end = instance.end_time
        ics_event.uid = f"{instance.id}@3TH"
        ics_event.description = instance.description
        ics_event.location = f"https://{instance.get_discord_message_url()}"  # Optional: Discord URL as location if relevant
        ics_event.created = instance.time_created

        calendar.events.add(ics_event)
    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))

    response = send_file(calendar_bytes, as_attachment=True, download_name=f"{event.name}.ics", mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename="{event.name}.ics"'
    return response