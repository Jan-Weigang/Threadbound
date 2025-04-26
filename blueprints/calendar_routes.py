from flask import session, request, redirect, render_template, url_for, abort
from flask import request, Blueprint, current_app
from flask_dance.contrib.discord import discord
from tt_calendar.models import *
from tt_calendar import utils

from datetime import datetime, timezone, timedelta

import json, logging


cal = Blueprint('cal_bp', __name__)



# ======================================
# ======== Calendar Endpoints ==========
# ======================================

@cal.route('/', defaults={'view_type': 'regular'}, methods=['GET'])
@cal.route('/<string:view_type>', methods=['GET'])
def view(view_type):
    if view_type not in ['public', 'regular', 'template']:
        abort(404)

    is_authenticated = False
    if session:
        is_authenticated = True

    user = {}
    user['name'] = session.get('username', None)
    user['is_member'] = session.get('is_member', None)
    user['member'] = "Ja" if session.get('is_member', None) else "Nein"
    user['beirat'] = "Ja" if session.get('is_beirat', None) else "Nein"
    user['vorstand'] = "Ja" if session.get('is_vorstand', None) else "Nein"
    user['admin'] = "Ja" if session.get('is_admin', None) else "Nein"
    user['id'] = session.get('user_id', None)

    logging.info(f"Calendar opened by {user['name']}, {user['is_member']=}")

    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()

    return render_template('view.html', view_type=view_type, date=date, is_authenticated=is_authenticated, user=user)



from blueprints.api_routes import prepare_reservations_for_jinja

#This takes no argument since they come from an html form.
@cal.route('/fetch/day')
def fetch_day():
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    view_type = request.args.get('view_type', 'public')

    reservations = prepare_reservations_for_jinja(view_type, date_str, date_str)
    tables = Table.query.order_by(Table.id).all() # Table ID must be ordered
    event_types = EventType.query.all()
    return render_template('partials/calendar_content.html', 
                           date=date, 
                           tables=tables, 
                           event_types=event_types,
                           reservations=reservations)


#This takes no argument since they come from an html form.
@cal.route('/fetch/month')
def fetch_month():
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    view_type = request.args.get('view_type', 'public')

    week_start, week_end = utils.get_end_days_of_week(date)
    date_range, first_date_str, last_date_str = utils.get_end_days_of_month(date)
    reservations = prepare_reservations_for_jinja(view_type, first_date_str, last_date_str)

    tables = Table.query.order_by(Table.id).all() # Table ID must be ordered
    event_types = EventType.query.all()

    occupancy_by_day = utils.get_occupancy_by_day(reservations, tables)

    today = datetime.now(timezone.utc).date()
    
    return render_template('partials/month_content.html', 
                           date=date, 
                           tables=tables, 
                           event_types=event_types,
                           reservations=reservations,
                           date_list=list(date_range),
                           week_start=week_start,
                           week_end=week_end,
                           occupancy_by_day=json.dumps(occupancy_by_day),
                           today=today)



@cal.route('/fetch/reservation/<string:event_id>')
def reservation_popup(event_id):
    user_id = session['user_id']

    # Fetch reservation and related data from the database
    reservation = Reservation.query.filter_by(event_id=event_id).first()

    # If no reservation is found, return a 404 error
    if reservation is None:
        abort(404)

    # Get only the needed data
    reservation_data = {
        'id': reservation.id,
        'user_name': reservation.user.username,
        'user_id': reservation.user.id,
        'event_id': reservation.event_id,
        'template_id': reservation.associated_event.template_id,
        'date': reservation.associated_event.start_time.strftime('%d.%m.%Y'),
        'start_time': reservation.associated_event.start_time.strftime('%H:%M'),
        'end_time': reservation.associated_event.end_time.strftime('%H:%M'),
        'game_category': reservation.associated_event.game_category.name,
        'name': reservation.associated_event.name,
        'description': reservation.associated_event.description,
        'time_created': reservation.associated_event.time_created.strftime('%d.%m.%Y %H:%M'),
        'time_updated': reservation.associated_event.time_updated.strftime('%d.%m.%Y %H:%M') if reservation.associated_event.time_updated else None,
        'publicity': reservation.associated_event.publicity.name,
        'discord_link': reservation.associated_event.get_discord_message_url()
    }

    if session.get('is_member', False):
        reservation_data['attendees'] = ', '.join([attendee.username for attendee in reservation.associated_event.attendees])
    else:
        reservation_data['attendees'] = len(reservation.associated_event.attendees)

    table = Table.query.get(reservation.table_id)
    event_type = EventType.query.get(reservation.associated_event.event_type_id)
    related_tables = Table.query.join(Reservation, Reservation.table_id == Table.id)\
                                .filter(Reservation.event_id == event_id)\
                                .all()
    relatedTablesInfo = ', '.join(table.name for table in related_tables)

    # Render the popup template with the fetched data
    return render_template('partials/calendar_reservation_popup.html', 
                           reservation=reservation_data, 
                           event_type=event_type, 
                           relatedTablesInfo=relatedTablesInfo,
                           user_id=user_id)

@cal.route('/shortcuts')
def popup_shortcuts():
    return render_template('partials/popup_shortcuts.html')

@cal.route('/tutorial')
def popup_tutorial():
    return render_template('partials/popup_tutorial.html')


@cal.route('/calendar/popup-userevents')
def popup_userevents():
    user = User.query.get(session['user_id'])
    assert user

    now = datetime.now(pytz.timezone('Europe/Berlin'))
    week_ago = now - timedelta(days=7)
    week_later = now + timedelta(days=7)

    events = Event.query.filter(
        Event.start_time.between(week_ago, week_later),
        Event.deleted == False,
    ).filter(
        (Event.user_id == user.id) | 
        (Event.attendees.any(id=user.id))
    ).order_by(Event.start_time).all()

    # Fetch own templates
    templates = Event.get_template_events().filter(
        Event.user_id == user.id
    )

    return render_template('partials/popup_userevents.html', events=events, templates=templates, current_user_id=user.id)
