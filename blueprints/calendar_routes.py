from flask import session, request, redirect, render_template, url_for, abort
from flask import request, Blueprint, current_app
from flask_dance.contrib.discord import discord

from datetime import datetime

# ======================================
# ======== Calendar Endpoints ==========
# ======================================

cal = Blueprint('cal_bp', __name__)


@cal.route('/month', methods=['GET'])
def month():
    return render_template('month.html')


@cal.route('/day', defaults={'view_type': 'regular'}, methods=['GET'])
@cal.route('/day/<string:view_type>', methods=['GET'])
def day(view_type):
    if view_type not in ['public', 'regular', 'template']:
        abort(404)

    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()

    if view_type != 'public':
        if not discord.authorized:
            return redirect(url_for('cal_bp.day', view_type='public'))
    return render_template('mycalendar.html', view_type=view_type, date=date)


@cal.route('/day2', defaults={'view_type': 'regular'}, methods=['GET'])
@cal.route('/day2/<string:view_type>', methods=['GET'])
def day2(view_type):
    if view_type not in ['public', 'regular', 'template']:
        abort(404)

    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()

    if view_type != 'public':
        if not discord.authorized:
            return redirect(url_for('cal_bp.day', view_type='public'))
    return render_template('day.html', view_type=view_type, date=date)



from blueprints.api_routes import prepare_reservations
from tt_calendar import utils
from tt_calendar.models import *

@cal.route('/fetch')
def fetch_calendar():
    date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    view_type = request.args.get('view_type', 'public')

    reservations = prepare_reservations(view_type, date_str, date_str)
    tables = Table.query.order_by(Table.id).all() # Table ID must be ordered
    event_types = EventType.query.all()
    return render_template('partials/calendar_content.html', 
                           date=date, 
                           tables=tables, 
                           event_types=event_types,
                           reservations=reservations)
