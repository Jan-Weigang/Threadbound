from flask import request, Blueprint, redirect, url_for, flash, render_template, current_app
from tt_calendar.models import *
from tt_calendar import decorators
from tt_calendar import utils

from flask import session

from exceptions import *

import logging


event_bp = Blueprint('event_bp', __name__)


@event_bp.route('/create', methods=['GET', 'POST'])
@decorators.login_required
def create_event():
    user_manager = current_app.config['user_manager']
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))

    if request.method == 'POST':
        
        form_data = utils.extract_event_form_data(request)
        if not form_data:
            return redirect(url_for('event_bp.create_event'))

        if request.form['collision'] != "true":
            # Check table availability only for normal bookings
            available, conflicting_table = utils.check_availability(
                form_data['start_datetime'],
                form_data['end_datetime'],
                form_data['table_ids']
            )
            if not available:
                flash(f'Table {conflicting_table} is already reserved for the selected time.', 'error')
                return redirect(url_for('event_bp.create_event'))

        # Create the event and reservations
        event_manager = current_app.config['event_manager']
        new_event = event_manager.create_event_from_form(user, form_data)
        logging.info(f"Created event {new_event.name}")

        event_date = form_data['start_datetime'].date().strftime('%Y-%m-%d')
        flash("Event created successfully.", "success")
        return redirect(url_for('cal_bp.view', date=event_date))


    # Get optional arguments from request
    requested_table_id = request.args.get('table_id')
    requested_start = request.args.get('time')
    requested_date = request.args.get('date')
    
    requested_start_time, requested_end_time = utils.get_rounded_event_times(requested_start)

    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()
    tables = Table.query.all()
    rooms = Room.query.all()

    return render_template('events/event_form.html', 
                           game_categories=game_categories, 
                           event_types=event_types, 
                           publicity_levels=publicity_levels, 
                           tables=tables,
                           rooms=rooms,
                           table_id=requested_table_id,
                           start_time=requested_start_time,
                           end_time=requested_end_time,
                           requested_date=requested_date
                           )


@event_bp.route('/edit/<string:event_id>', methods=['GET', 'POST'])
@decorators.login_required
def edit_event(event_id):
    user_manager = current_app.config['user_manager']
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))
    
    is_allowed = session.get('is_admin') or session.get('is_vorstand')
    event = Event.query.get_or_404(event_id)

    # Ensure the user is the creator of the event
    if event.user_id != user.id and not is_allowed:
        flash('You are not authorized to edit this event.', 'error')
        return redirect(url_for('cal_bp.view'))  # Redirect to the event listing or another page

    tables = Table.query.all()
    rooms = Room.query.all()

    if request.method == 'POST':
        form_data = utils.extract_event_form_data(request)
        if not form_data:
            return redirect(url_for('event_bp.edit_event', event_id=event_id))
        
        if request.form['collision'] != "true":
        # Check table availability except for already reserved by this event
            available, conflicting_table = utils.check_availability(
                form_data['start_datetime'],
                form_data['end_datetime'],
                form_data['table_ids'],
                exclude_event_id=event_id
            )
            if not available:
                flash(f'Table {conflicting_table} is already reserved for the selected time.', 'error')
                return redirect(url_for('event_bp.edit_event', event_id=event_id))
        
        try:
            event_manager = current_app.config['event_manager']
            event_manager.update_event_from_form(event, form_data)
        except Exception as e:
            flash(f"An error occurred while updating the event: {e}", "danger")
            return redirect(url_for('event_bp.edit_event', event_id=event.id))

        event_date = form_data['start_datetime'].date().strftime('%Y-%m-%d')
        return redirect(url_for('cal_bp.view', date=event_date))


    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()
    requested_start_time = event.start_time.strftime('%H:%M')
    requested_end_time = event.end_time.strftime('%H:%M')
    requested_date = event.start_time.date()

    return render_template('events/event_form.html', 
                           event=event, 
                           game_categories=game_categories, 
                           event_types=event_types, 
                           publicity_levels=publicity_levels,
                           tables=tables,
                           rooms=rooms,
                           start_time=requested_start_time,
                           end_time=requested_end_time,
                           requested_date=requested_date)


@event_bp.route('/delete/<string:event_id>', methods=['POST'])
@decorators.login_required
def delete_event(event_id):
    user_manager = current_app.config['user_manager']
    event_manager = current_app.config['event_manager']
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))
    event = Event.query.get_or_404(event_id)
    event_date = event.start_time.date().strftime('%Y-%m-%d')

    action = request.form.get('action', 'cancel')

    # Ensure the user is the creator of the event
    if event.user_id != user.id: # type:ignore
        flash('You are not authorized to edit this event.', 'error')
        return redirect(url_for('cal_bp.view'))  # Redirect to the event listing or another page

    try:
        discord_handler = current_app.config['discord_handler']
        discord_handler.post_to_discord(event, action)
        discord_handler.send_deletion_notice(event)
        # Delete the event
        event_manager.delete_event(event)
        return redirect(url_for('cal_bp.view', date=event_date))
    except Exception as e:
        # If there is an error, roll back the transaction
        flash(f"An error occurred while deleting the event: {e}", "danger")
        return redirect(url_for('event_bp.edit_event', event_id=event_id))