from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from tt_calendar.models import Table, GameCategory, EventType, Publicity, Event
from tt_calendar import decorators, utils

from datetime import datetime
import pytz, logging

from exceptions import *

from flask import session


template_bp = Blueprint("template_bp", __name__)

# HELPER FUNCTIONS


def build_rrule_from_form(form_data: dict) -> str:
    """
    Builds an RRULE string based on form fields: frequency, interval, byday, byday_single, bysetpos, end-date.
    """
    freq = form_data.get("frequency")
    interval = form_data.get("interval")
    byday = form_data.get("byday")
    byday_single = form_data.get("byday_single")
    bysetpos = form_data.get("bysetpos")

    end_date = form_data.get("end-date")
    end_template = form_data.get("end_template")

    if not freq:
        return ""

    rrule_parts = [f"FREQ={freq}"]

    if freq == "WEEKLY" and byday and interval:
        rrule_parts.append(f"INTERVAL={interval}")
        rrule_parts.append(f"BYDAY={byday}")

    if freq == "MONTHLY" and byday_single and bysetpos:
        rrule_parts.append(f"BYDAY={bysetpos}{byday_single}")

    if end_template:  # Checkbox is checked
        if end_date:
            # Format the end date properly: 23:59:59 at the end of the day, UTC
            end_datetime = end_date.replace("-", "") + "T235959Z"
            rrule_parts.append(f"UNTIL={end_datetime}")

    return ";".join(rrule_parts)


# ROUTES


@template_bp.route("/create", methods=["GET", "POST"])
@decorators.require_min_role('beirat')
def create_template():
    user_manager = current_app.config['user_manager']
    
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))

    is_allowed = session.get('is_admin') or session.get('is_vorstand') or session.get('is_beirat')

    # Check if the user is allowed to create a template (Beirat or Vorstand roles)
    if not is_allowed:
        flash("You do not have permission to create a template.", "danger")
        return redirect(url_for("cal_bp.view", view_type="regular"))
    
    logging.info(f"Template creating is {user.username} with id {user.discord_id}. member: {session['is_member']} - admin: {session['is_admin']}") # type: ignore

    if request.method == "POST":
        form_data = utils.extract_template_form_data(request)
        if not form_data:
            return redirect(url_for("template_bp.create_template"))

        rrule = build_rrule_from_form(request.form)
        form_data['recurrence_rule'] = rrule
        form_data['is_template'] = True

        event_manager = current_app.config['event_manager']
        template_event = event_manager.create_template_from_form(user, form_data)
        logging.info(f"Created Template {template_event.name}")

        event_date = form_data['start_datetime'].date().strftime('%Y-%m-%d')
        flash("Template created successfully.", "success")
        return redirect(url_for("cal_bp.view", view_type="regular", date=event_date))
    
    # Preload form values
    requested_table_id = request.args.get("table_id")
    requested_start = request.args.get("time")
    requested_date = request.args.get("date")

    requested_start_time, requested_end_time = utils.get_rounded_event_times(requested_start)

    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()
    tables = Table.query.all()

    return render_template(
        "events/event_form.html",
        game_categories=game_categories,
        event_types=event_types,
        publicity_levels=publicity_levels,
        tables=tables,
        table_id=requested_table_id,
        start_time=requested_start_time,
        end_time=requested_end_time,
        requested_date=requested_date,
        is_template=True
    )


@template_bp.route("/edit/<string:event_id>", methods=["GET", "POST"])
@decorators.require_min_role('beirat')
def edit_template(event_id):
    user_manager = current_app.config['user_manager']
    try:
        user = user_manager.get_or_create_user()
    except UserNotAuthenticated:
        return redirect(url_for("discord.login"))

    event = Event.query.get_or_404(event_id)
    is_allowed = session.get('is_admin') or session.get('is_vorstand')

    # Ensure the user is the creator of the event
    if event.user_id != user.id and not is_allowed:
        flash('You are not authorized to edit this event.', 'error')
        return redirect(url_for('cal_bp.view'))  # Redirect to the event listing or another page


    if not event.is_template:
        flash("This event is not a template.", "danger")
        return redirect(url_for("cal_bp.view", view_type="regular"))

    tables = Table.query.all()

    if request.method == "POST":
        form_data = utils.extract_template_form_data(request)
        if not form_data:
            return redirect(url_for("template_bp.edit_template", event_id=event_id))

        rrule = build_rrule_from_form(request.form)
        form_data['recurrence_rule'] = rrule

        try:
            event_manager = current_app.config['event_manager']
            event_manager.update_event_from_form(event, form_data)
        except Exception as e:
            flash(f"An error occurred while updating the template: {e}", "danger")
            return redirect(url_for("template_bp.edit_template", event_id=event_id))

        flash("Template updated successfully.", "success")
        return redirect(url_for("cal_bp.view", view_type="regular"))

    # Preload form values
    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()
    publicity_levels = Publicity.query.all()

    requested_start_time = event.start_time.strftime("%H:%M")
    requested_end_time = event.end_time.strftime("%H:%M")
    requested_date = event.start_time.date()

    return render_template(
        "events/event_form.html",
        event=event,
        game_categories=game_categories,
        event_types=event_types,
        publicity_levels=publicity_levels,
        tables=tables,
        start_time=requested_start_time,
        end_time=requested_end_time,
        requested_date=requested_date,
        is_template=True
    )
