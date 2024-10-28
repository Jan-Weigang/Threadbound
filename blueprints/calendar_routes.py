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

    date = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))

    if view_type != 'public':
        if not discord.authorized:
            return redirect(url_for('cal_bp.day', view_type='public'))
    return render_template('mycalendar.html', view_type=view_type, date=date)