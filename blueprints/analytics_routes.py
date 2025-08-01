from flask import Blueprint, render_template, request, current_app, session, jsonify, redirect, url_for
from tt_calendar.models import db, Event, Reservation, GameCategory, EventType, User
from tt_calendar import decorators
from tt_calendar import utils
from datetime import datetime, timedelta
import pytz

from sqlalchemy import func

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

    if not is_admin:
        return redirect(url_for('cal_bp.view'))

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

    results = (
        query.join(GameCategory)
            .join(EventType)
            .with_entities(GameCategory.name, EventType.name, db.func.count(Event.id))
            .group_by(GameCategory.name, EventType.name)
            .order_by(GameCategory.name, db.func.count(Event.id).desc())
            .all()
    )

    from collections import defaultdict

    tree = defaultdict(lambda: defaultdict(int))

    # Build nested dict: {category: {event_type: count}}
    for category, event_type, count in results:
        tree[category][event_type] += count
        
    # Build sunburst-style nested list
    sunburst_data = [
        {
            "name": category,
            "children": [
                {"name": event_type, "value": count}
                for event_type, count in types.items()
            ]
        } for category, types in tree.items()
    ]
    
    return jsonify({"data": sunburst_data})



@analytics_bp.route("/chart/events-per-week", methods=["POST"])
def chart_events_per_week():
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

    if game_category_id:
        results = query \
            .with_entities(
                func.strftime('%Y-W%W', Event.start_time).label('week'),
                EventType.name,
                func.count(Event.id)
            ) \
            .join(EventType) \
            .group_by('week', EventType.name) \
            .order_by('week') \
            .all()
    else:
        results = query \
            .with_entities(
                func.strftime('%Y-W%W', Event.start_time).label('week'),
                GameCategory.name,
                func.count(Event.id)
            ) \
            .join(GameCategory) \
            .group_by('week', GameCategory.name) \
            .order_by('week') \
            .all()

    # Detect unique weeks and series
    data_by_series = defaultdict(lambda: defaultdict(int))
    week_set = set()

    for week, name, count in results:
        data_by_series[name][week] += count
        week_set.add(week)

    weeks = sorted(week_set)
    series = []
    for series_name, week_map in data_by_series.items():
        series.append({
            "name": series_name,
            "type": "bar",
            "data": [week_map.get(w, 0) for w in weeks]
        })

    return jsonify({"weeks": weeks, "series": series})


@analytics_bp.route("/table/events-matrix", methods=["POST"])
def table_events_matrix():
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

    results = (
        query.join(GameCategory)
             .join(EventType)
             .with_entities(GameCategory.name, EventType.name, db.func.count(Event.id))
             .group_by(GameCategory.name, EventType.name)
             .all()
    )

    from collections import defaultdict
    matrix = defaultdict(lambda: defaultdict(int))
    row_totals = defaultdict(int)
    col_totals = defaultdict(int)
    all_categories = set()
    all_types = set()

    for cat, etype, count in results:
        matrix[cat][etype] = count
        row_totals[cat] += count
        col_totals[etype] += count
        all_categories.add(cat)
        all_types.add(etype)

    all_categories = sorted(all_categories)
    all_types = sorted(all_types)

    return render_template("analytics/event_matrix_table.html",
                           matrix=matrix,
                           row_totals=row_totals,
                           col_totals=col_totals,
                           categories=all_categories,
                           types=all_types)
