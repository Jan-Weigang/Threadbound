from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from tt_calendar.models import Table, GameCategory, EventType, Publicity
from tt_calendar import decorators, utils

from datetime import datetime
import pytz


template_bp = Blueprint("template_bp", __name__)


@template_bp.route("/create", methods=["GET", "POST"])
@decorators.login_required
def create_template():
    user_manager = current_app.config['user_manager']
    user = user_manager.get_or_create_user()

    if request.method == "POST":
        form_data = utils.extract_template_form_data(request)
        if not form_data:
            return redirect(url_for("template_bp.create_template"))

        # Construct RRULE string from form inputs
        freq = request.form.get("frequency")
        interval = request.form.get("interval")
        byday = request.form.get("byday")
        byday_single = request.form.get("byday_single")
        bysetpos = request.form.get("bysetpos")

        rrule_parts = [f"FREQ={freq}"]
        if interval:
            rrule_parts.append(f"INTERVAL={interval}")
        if freq == "WEEKLY" and byday:
            rrule_parts.append(f"BYDAY={byday}")
        if freq == "MONTHLY" and byday_single and bysetpos:
            rrule_parts.append(f"BYDAY={bysetpos}{byday_single}")

        form_data['is_template'] = True
        form_data['recurrence_rule'] = ";".join(rrule_parts)

        event_manager = current_app.config['event_manager']
        template_event = event_manager.create_template_from_form(user, form_data)

        flash("Template created successfully.", "success")
        return redirect(url_for("cal_bp.view", view_type="template"))
    
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
