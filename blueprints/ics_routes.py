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
    ics_event = ICSEvent()
    
    ics_event.name = event.name
    ics_event.begin = event.start_time.isoformat()
    ics_event.end = event.end_time.isoformat()
    ics_event.uid = f"{event_id}@3TH"
    ics_event.description = event.description
    ics_event.location = f"https://{event.get_discord_message_url()}"  # Optional: Discord URL as location if relevant
    ics_event.created = datetime.now(pytz.utc)

    calendar.events.add(ics_event)
    calendar_bytes = BytesIO(calendar.serialize().encode('utf-8'))

    response = send_file(calendar_bytes, as_attachment=True, download_name=f"{event.name}.ics", mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename="{event.name}.ics"'
    return response