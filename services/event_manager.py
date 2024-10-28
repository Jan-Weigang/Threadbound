# services/event_manager.py

from tt_calendar.models import Event, Reservation, db
from tt_calendar import utils

class EventManager:
    def __init__(self, discord_handler):
        self.discord_handler = discord_handler

    def create_event_in_db(self, user, form_data):
        form_data['start_datetime_utc'] = utils.convert_to_utc(form_data['start_datetime'])
        form_data['end_datetime_utc'] = utils.convert_to_utc(form_data['end_datetime'])

        new_event = Event(
            name=form_data['name'], # type: ignore
            description=form_data['description'], # type: ignore
            game_category_id=int(form_data['game_category_id']), # type: ignore
            event_type_id=int(form_data['event_type_id']), # type: ignore
            publicity_id=int(form_data['publicity_id']), # type: ignore
            start_time=form_data['start_datetime_utc'], # type: ignore
            end_time=form_data['end_datetime_utc'], # type: ignore
            user_id=user.id, # type: ignore
        )
        db.session.add(new_event)

        try:
            Reservation.query.filter_by(event_id=new_event.id).delete()
            self.create_reservations(user, new_event, form_data['table_ids'])

            message_id = self.discord_handler.post_to_discord(new_event, action="update")
            if message_id:
                new_event.discord_post_id = message_id

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"Error during event creation: {e}")
            raise

        return new_event

    def update_event_in_db(self, event, user, form_data):
        form_data['start_datetime_utc'] = utils.convert_to_utc(form_data['start_datetime'])
        form_data['end_datetime_utc'] = utils.convert_to_utc(form_data['end_datetime'])

        event.name = form_data['name']
        event.description = form_data['description']
        event.game_category_id = int(form_data['game_category_id'])
        event.event_type_id = int(form_data['event_type_id'])
        event.publicity_id = int(form_data['publicity_id'])
        event.start_time = form_data['start_datetime_utc']
        event.end_time = form_data['end_datetime_utc']
        event.user_id = user.id

        try:
            Reservation.query.filter_by(event_id=event.id).delete()
            self.create_reservations(user, event, form_data['table_ids'])

            message_id = self.discord_handler.post_to_discord(event, action="update")
            if message_id:
                event.discord_post_id = message_id

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"Error during event update: {e}")
            raise

        return event

    def create_reservations(self, user, new_event, table_ids):
        for table_id in table_ids:
            reservation = Reservation(
                user_id=user.id, # type: ignore
                event_id=new_event.id, # type: ignore
                table_id=table_id # type: ignore
            )
            db.session.add(reservation)
        db.session.commit()
