from flask import Blueprint, render_template, request, current_app, session
from tt_calendar.models import db, Event, Reservation, GameCategory, EventType, User
from tt_calendar import decorators
from tt_calendar import utils
from datetime import datetime, timedelta
import pytz

analytics_bp = Blueprint('analytics_bp', __name__)

# HELPER FUNCTIONS

from collections import Counter, defaultdict

def calculate_statistics(events):
    stats = {}

    # Basic counts
    stats['total_events'] = len(events)

    if not events:
        return stats  # early exit if empty

    # Counters
    user_counter = Counter()
    event_type_counter = Counter()
    game_category_counter = Counter()
    attendee_counts = []

    for event in events:
        user_counter[event.user.username] += 1
        event_type_counter[event.event_type.name] += 1
        game_category_counter[event.game_category.name] += 1
        attendee_counts.append(len(event.attendees))

    # Aggregate
    stats['events_per_user'] = user_counter.most_common()
    stats['events_per_event_type'] = event_type_counter.most_common()
    stats['events_per_game_category'] = game_category_counter.most_common()

    # Average attendees
    stats['average_attendees'] = round(sum(attendee_counts) / len(attendee_counts), 2)

    # Template vs Ad-Hoc
    template_events = [e for e in events if e.is_template]
    stats['template_event_count'] = len(template_events)
    stats['ad_hoc_event_count'] = stats['total_events'] - len(template_events)

    return stats


# ROUTES


@analytics_bp.route('/', methods=['GET'])
@decorators.login_required
def view_stats():
    # Only allow user to see their own data unless admin
    user_id = session.get('user_id')
    is_admin = session.get('is_admin') or session.get('is_vorstand')

    # Preload filter options
    users = User.query.all() if is_admin else [User.query.get(user_id)]
    game_categories = GameCategory.query.all()
    event_types = EventType.query.all()

    # Prefill dates
    today = datetime.now(pytz.timezone('Europe/Berlin')).date()
    first_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    return render_template('analytics/stats_dashboard.html',
                           users=users,
                           user_id=user_id,
                           game_categories=game_categories,
                           event_types=event_types,
                           is_admin=is_admin,
                           start_date_prefill=first_of_last_month.strftime('%Y-%m-%d'),
                           end_date_prefill=today.strftime('%Y-%m-%d'))


@analytics_bp.route('/stats/data', methods=['POST'])
@decorators.login_required
def fetch_stats_data():
    data = request.form
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    user_id = data.get('user_id')
    game_category_id = data.get('game_category_id')
    event_type_id = data.get('event_type_id')

    query = Event.query.filter(Event.start_time.between(start_date, end_date))

    if user_id:
        query = query.filter(Event.user_id == user_id)
    if game_category_id:
        query = query.filter(Event.game_category_id == game_category_id)
    if event_type_id:
        query = query.filter(Event.event_type_id == event_type_id)

    events = query.all()

    # TODO: Process the events into statistics
    stats = calculate_statistics(events)

    return render_template('analytics/stats_result.html', stats=stats)


@analytics_bp.route("/chart/events-per-category", methods=["POST"])
def chart_events_per_category():
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    game_category_id = request.form.get("game_category_id")
    user_id = request.form.get("user_id")
    event_type_id = request.form.get("event_type_id")

    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = utils.convert_to_berlin_time(start_date)
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = utils.convert_to_berlin_time(end_date)


    query = Event.get_regular_events()

    if start_date:
        query = query.filter(Event.start_time >= start_date)
    if end_date:
        query = query.filter(Event.start_time <= end_date)
    if game_category_id:
        query = query.filter_by(game_category_id=game_category_id)
    if user_id:
        query = query.filter(Event.user_id == user_id)
    if event_type_id:
        query = query.filter(Event.event_type_id == event_type_id)

    results = query.with_entities(GameCategory.name, db.func.count(Event.id))\
        .join(GameCategory)\
        .group_by(GameCategory.name)\
        .order_by(db.func.count(Event.id).desc())\
        .all()

    labels = [r[0] for r in results]
    values = [r[1] for r in results]

    return render_template('analytics/charts/events_per_category.html', labels=labels, values=values)

