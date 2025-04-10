from flask import session, request, jsonify
from flask import request, Blueprint, current_app
from flask_dance.contrib.discord import discord
from tt_calendar.models import db, User, GameCategory, EventType, Publicity, Event, Table, Reservation, Overlap, EventState
from datetime import datetime, time
from sqlalchemy import or_, and_

from tt_calendar import decorators
from tt_calendar import utils
import json

# ======================================
# ========== API Endpoints =============
# ======================================

api = Blueprint('api_bp', __name__)

@api.route('/users', methods=['GET'])
@decorators.login_required
def api_get_users():
    users = User.query.all()
    user_data = [{'id': user.id, 'discord_id': user.discord_id, 'username': user.username} for user in users]
    # print(json.dumps(user_data, indent=4))
    return jsonify({'users': user_data})

# POST endpoint to add a user (if needed)
@api.route('/users', methods=['POST'])
def api_create_user():
    data = request.get_json()
    new_user = User(discord_id=data['discord_id'], username=data['username']) # type: ignore
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@api.route('/game-categories', methods=['GET'])
def api_get_game_categories():
    categories = GameCategory.query.all()
    category_data = [{'id': category.id, 'name': category.name, 'icon': category.icon} for category in categories]
    # print(json.dumps(category_data, indent=4))
    return jsonify({'game_categories': category_data})

# POST endpoint to add a new game category (if needed)
@api.route('/game-categories', methods=['POST'])
def api_create_game_category():
    data = request.get_json()
    new_category = GameCategory(name=data['name'], icon=data['icon']) # type: ignore
    db.session.add(new_category)
    db.session.commit()
    return jsonify({'message': 'Game Category created successfully'}), 201

@api.route('/event-types', methods=['GET'])
def api_get_event_types():
    event_types = EventType.query.all()
    event_type_data = [{'id': event_type.id, 'name': event_type.name, 'color': event_type.color} for event_type in event_types]
    # print(json.dumps(event_type_data, indent=4))
    return jsonify({'event_types': event_type_data})

# POST endpoint to add a new event type (if needed)
@api.route('/event-types', methods=['POST'])
def api_create_event_type():
    data = request.get_json()
    new_event_type = EventType(name=data['name'], color=data['color']) # type: ignore
    db.session.add(new_event_type)
    db.session.commit()
    return jsonify({'message': 'Event Type created successfully'}), 201

@api.route('/publicities', methods=['GET'])
def api_get_publicities():
    publicities = Publicity.query.all()
    publicity_data = [{'id': publicity.id, 'name': publicity.name} for publicity in publicities]
    # print(json.dumps(publicity_data, indent=4))
    return jsonify({'publicities': publicity_data})

# POST endpoint to add new publicity (if needed)
@api.route('/publicities', methods=['POST'])
def api_create_publicity():
    data = request.get_json()
    new_publicity = Publicity(name=data['name']) # type: ignore
    db.session.add(new_publicity)
    db.session.commit()
    return jsonify({'message': 'Publicity created successfully'}), 201

@api.route('/events', methods=['GET'])
@decorators.login_required
def api_get_events():
    events = Event.get_regular_events().all()
    event_data = [{
        'id': event.id,
        'name': event.name,
        'description': event.description,
        'game_category_id': event.game_category_id,
        'event_type_id': event.event_type_id,
        'publicity_id': event.publicity_id,
        'start_time': event.start_time.isoformat(),
        'end_time': event.end_time.isoformat(),
        'discord_post_id': event.discord_post_id,
        'time_created': event.time.isoformat(),
    } for event in events]
    # print(json.dumps(event_data, indent=4))
    return jsonify({'events': event_data})


@api.route('/events', methods=['POST'])
def api_create_event():
    data = request.get_json()

    # Check table availability before creating the event
    start_datetime = datetime.fromisoformat(data['start_time'])
    end_datetime = datetime.fromisoformat(data['end_time'])
    table_ids = data['table_ids']

    available, conflicting_table = utils.check_availability(start_datetime, end_datetime, table_ids)
    if not available:
        return jsonify({'error': f'Table {conflicting_table} is already reserved for the selected time.'}), 409

    # Create the event
    new_event = Event(
        name=data['name'], # type: ignore
        description=data.get('description', None), # type: ignore
        game_category_id=int(data['game_category_id']), # type: ignore
        event_type_id=int(data['event_type_id']), # type: ignore
        publicity_id=int(data['publicity_id']), # type: ignore
        start_time=start_datetime, # type: ignore
        end_time=end_datetime, # type: ignore
        discord_post_id=data.get('discord_post_id', None), # type: ignore
        time_created=datetime.utcnow() # type: ignore
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({'message': 'Event created successfully'}), 201


@api.route('/tables', methods=['GET'])
def api_get_tables():
    tables = Table.query.all()
    table_data = [{'id': table.id, 'name': table.name, 'type': table.type, 'capacity': table.capacity} for table in tables]
    # print(json.dumps(table_data, indent=4))
    return jsonify({'tables': table_data})

# POST endpoint to add a new table (if needed)
@api.route('/tables', methods=['POST'])
def api_create_table():
    data = request.get_json()
    new_table = Table(name=data['name'], type=data['type'], capacity=data['capacity']) # type: ignore
    db.session.add(new_table)
    db.session.commit()
    return jsonify({'message': 'Table created successfully'}), 201

@api.route('/reservations/<string:view_type>', methods=['GET'])
def api_get_reservations(view_type=None):
    current_date = utils.convert_to_berlin_time(datetime.utcnow()).strftime('%Y-%m-%d')
    date_param = request.args.get('date', current_date)
    end_date_param = request.args.get('end_date', date_param)

    reservation_data = prepare_reservations_for_jinja(date_param=date_param, end_date_param=end_date_param, view_type=view_type)
    
    # print(json.dumps(reservation_data, indent=4))
    return jsonify({'reservations': reservation_data})


def prepare_reservations_for_jinja(view_type, date_param, end_date_param):
    print(f"Triggered prepare with {view_type}, {date_param}, {end_date_param}")
    if discord.authorized is None:
        # If the user is not authenticated, only load events with publicity 3
        reservations = Reservation.get_regular_reservations().filter(Reservation.associated_event.has(publicity_id=3)).all() # type:ignore
    else:
        if not view_type:
            view_type = 'regular' 
        

        if view_type == 'template':
            reservations = Reservation.get_template_reservations().all()
        elif view_type == 'regular':
            reservations = Reservation.get_regular_reservations().all()      # type:ignore
        elif view_type == 'public':
            reservations = Reservation.get_regular_reservations().filter(
                Reservation.associated_event.has(publicity_id=3, is_published=True)).all()         # type:ignore
        else:
            reservations = Reservation.get_regular_reservations().all()

    # Filter reservations by the date if provided
    if date_param and end_date_param:
        try:
            start_date = datetime.strptime(date_param, '%Y-%m-%d')  # Expected format: 'YYYY-MM-DD'
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d')

            reservations = [r for r in reservations if start_date.date() <= r.associated_event.start_time.date() <= end_date.date()]
        
            # selected_date = datetime.strptime(date_param, '%Y-%m-%d')  # Expected format: 'YYYY-MM-DD'
            # reservations = [r for r in reservations if r.associated_event.start_time.date() == selected_date.date()]
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
    # **Sort by date and start_time**
    reservations.sort(key=lambda r: r.associated_event.start_time)
    
    reservation_data = [{
        'id': reservation.id,
        'user_name': reservation.user.username,
        'event_id': reservation.event_id,
        'table_id': reservation.table_id,
        'date': reservation.associated_event.start_time.date(),
        'start_time': reservation.associated_event.start_time.isoformat(),
        'end_time': reservation.associated_event.end_time.isoformat(),
        'start_time_str': reservation.associated_event.start_time.strftime('%H:%M'),
        'end_time_str': reservation.associated_event.end_time.strftime('%H:%M'),
        'game_category_icon': reservation.associated_event.game_category.icon,
        'game_category': reservation.associated_event.game_category.name,
        'name': reservation.associated_event.name,
        'description': reservation.associated_event.description,
        'event_type_id': reservation.associated_event.event_type_id,
        'attendee_count': len(reservation.associated_event.attendees),
        'time_created': reservation.associated_event.time_created.strftime('%d.%m.%Y %H:%M'),
        'time_updated': reservation.associated_event.time_updated.strftime('%d.%m.%Y %H:%M') if reservation.associated_event.time_updated else None,
        'publicity': reservation.associated_event.publicity.name,
        'discord_link': reservation.associated_event.get_discord_message_url(),
        'is_template': reservation.associated_event.is_template,
        'is_marked': not reservation.associated_event.is_published or reservation.associated_event.is_template
    } for reservation in reservations]

    if not discord.authorized or not session.get('is_member', False):
        for entry in reservation_data:
            entry['user_name'] = 'Mitglied' 
            # del entry['attendee_count']

    return reservation_data



# POST endpoint to add a new reservation (if needed)
@api.route('/reservations', methods=['POST'])
def api_create_reservation():
    data = request.get_json()
    new_reservation = Reservation(
        user_id=data['user_id'], # type: ignore
        event_id=data['event_id'], # type: ignore
        table_id=data['table_id'], # type: ignore
    )
    db.session.add(new_reservation)
    db.session.commit()
    return jsonify({'message': 'Reservation created successfully'}), 201



@api.route('/check_table_availability', methods=['POST'])
def check_table_availability():
    data = request.get_json()
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    exclude_event_id = data.get('exclude_event_id')

    if not date or not start_time or not end_time:
        return jsonify({'error': 'Date, start time, and end time are required.'}), 400

    # Convert date, start_time, and end_time to datetime objects
    start_datetime = datetime.strptime(f"{date}T{start_time}", '%Y-%m-%dT%H:%M')
    end_datetime = datetime.strptime(f"{date}T{end_time}", '%Y-%m-%dT%H:%M')

    start_datetime = utils.localize_to_berlin_time(start_datetime)
    end_datetime = utils.localize_to_berlin_time(end_datetime)

    # print(f"checkinc availability on date {date}")

    tables = Table.query.all()
    table_availability = []


    for table in tables:
        # print(f"Testing table: {table.id}")
        # Build the conditions
        conditions = [
            Event.start_time < end_datetime,
            Event.end_time > start_datetime
        ]
        
        # Conditionally add the exclude_event_id check if it's provided
        if exclude_event_id:
            conditions.append(Event.id != exclude_event_id)
            # print(f"Excluding event with id {exclude_event_id}")

        # Filter reservations based on the conditions
        reservations = Reservation.get_regular_reservations().filter(
            Reservation.table_id == table.id,
            Reservation.associated_event.has( # type: ignore
                and_(*conditions)  # Unpack the conditions list into the and_ function
            )
        ).all()

        earliest_available_start = datetime.combine(start_datetime.date(), time(hour=8, minute=0))
        latest_possible_end = datetime.combine(start_datetime.date(), time(hour=23, minute=59))
        
        if reservations:
            events_on_date = [reservation.associated_event for reservation in reservations]
            events_on_date.sort(key=lambda event: event.start_time)
            # # Calculate the earliest available start and latest possible end times for the table
            # events_on_date = Event.query.filter(
            #     Event.reservations.any(Reservation.table_id == table.id),
            #     Event.start_time >= datetime.combine(start_datetime.date(), time.min),
            #     Event.start_time <= datetime.combine(start_datetime.date(), time.max)
            # ).order_by(Event.start_time).all()

            if events_on_date:
                # Determine the earliest available start time and the latest possible end time for the day
                for event in events_on_date:
                    if event.end_time <= end_datetime:
                        earliest_available_start = event.end_time
                    if event.start_time >= start_datetime:
                        latest_possible_end = event.start_time
                    if event.end_time > end_datetime and event.start_time < start_datetime:
                        earliest_available_start = event.end_time
                        latest_possible_end = event.start_time

                # if not earliest_available_start:
                #     earliest_available_start = start_datetime.replace(hour=0, minute=0)
                # if not latest_possible_end:
                #     latest_possible_end = end_datetime.replace(hour=23, minute=59)

            table_availability.append({
                'table_id': table.id,
                'available': False,
                'earliest_available_start': earliest_available_start.strftime('%H:%M') if earliest_available_start else None,
                'latest_possible_end': latest_possible_end.strftime('%H:%M') if latest_possible_end else None
            })
        else:
            # The table is available for the selected time range
            table_availability.append({
                'table_id': table.id,
                'available': True,
                'earliest_available_start': earliest_available_start.strftime('%H:%M'),
                'latest_possible_end': latest_possible_end.strftime('%H:%M')
            })

    return jsonify({'tables': table_availability})


# @api.route('register_user', methods=['POST'])
# def register_user():
#     data = request.get_json()

#     # Extract the message_id, username, and action from the request data
#     message_id = data.get('message_id')
#     username = data.get('username')
#     action = data.get('action')  # "attend", "maybe", "not_attend"

#     if not message_id or not username or not action:
#         return jsonify({"error": "Missing data"}), 400
    
#     # Call the function to process the registration (add user to event)
#     result = register_user_for_event(message_id, username, action)

#     return jsonify(result), 200



@api.route('/attendance', methods=['POST'])
def handle_attendance():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data in request."}), 500
    
    discord_user_id = data.get('discord_user_id')
    message_id = data.get('message_id')
    action = data.get('action')

    print(f"user id {discord_user_id}  message id {message_id}   action {action}")
    try:
        event = Event.get_regular_events().filter_by(discord_post_id=message_id).first()
        if not event:
            return jsonify({"status": "error", "message": "Event not found"}), 404

        user = User.query.filter_by(discord_id=discord_user_id).first()
        if not user:
            user = User(discord_id=discord_user_id, username=data.get('username')) # type: ignore
            db.session.add(user)
            db.session.commit()
            user = User.query.filter_by(discord_id=discord_user_id).first()

        if action == "attend":
            if user not in event.attendees:
                event.attendees.append(user)
        elif action == "not_attend":
            if user in event.attendees:
                event.attendees.remove(user)

        db.session.commit()

        discord_handler = current_app.config['discord_handler']
        discord_handler.post_to_discord(event, action='update')

        return jsonify({"status": "success", "message": f"User marked as {action} for event."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    


@api.route('/resolve_overlap', methods=['POST'])
def resolve_overlap():
    data = request.json

    if not data:
        return jsonify({"status": "error", "message": "No data in request."}), 500

    try:
        discord_user_id = int(data.get('discord_user_id'))
        channel_id = int(data.get('channel_id'))  # ← now this instead of message_id
    except:
        return jsonify({"status": "error", "message": "Error in integer fields."}), 400
    
    # get validated bool if new should overwrite old
    prefer_new = data.get("prefer_new")
    if prefer_new not in [True, False, 'true', 'false', 'True', 'False', 0, 1]:
        return jsonify({"status": "error", "message": "Missing or invalid 'prefer_new' flag."}), 400
    prefer_new = str(prefer_new).lower() in ['true', '1']

    is_vorstand = data.get("prefer_new")
    if is_vorstand not in [True, False, 'true', 'false', 'True', 'False', 0, 1]:
        return jsonify({"status": "error", "message": "Missing or invalid 'prefer_new' flag."}), 400
    is_vorstand = str(is_vorstand).lower() in ['true', '1']

    if not all([discord_user_id, channel_id, prefer_new, is_vorstand]):
        return jsonify({"status": "error", "message": "Missing required fields."}), 400
    
    print(f"{discord_user_id=} {channel_id=} {prefer_new=} {is_vorstand=}")

    # Find overlap by Discord channel ID
    overlap = Overlap.query.filter_by(request_discord_channel_id=channel_id).first()
    if not overlap:
        return jsonify({"status": "error", "message": "Overlap not found."}), 404

    user = User.query.filter_by(discord_id=discord_user_id).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 403
    
    discord_handler = current_app.config['discord_handler']

    # Permission check
    is_creator_requesting = str(user.discord_id) == str(overlap.requesting_event.user.discord_id)
    is_creator_existing   = str(user.discord_id) == str(overlap.existing_event.user.discord_id)

    if not (is_creator_requesting or is_creator_existing or is_vorstand):
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Actual Function:

    event_manager = current_app.config['event_manager']
    if not prefer_new and (is_creator_requesting or is_vorstand):
        # event_manager.delete_event(overlap.requesting_event)
        overlap.resolve_overlap(EventState.DENIED)
        deleted = "requesting event"
    elif prefer_new and (is_creator_existing or is_vorstand):
        # event_manager.delete_event(overlap.existing_event)
        overlap.resolve_overlap(EventState.APPROVED)
        deleted = "existing event"
    else:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    db.session.commit()
    event_manager.event_state_handler(overlap.requesting_event)
    return jsonify({"status": "success", "message": f"{deleted} deleted by creator."})

