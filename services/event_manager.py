# services/event_manager.py

from tt_calendar.models import Event, Reservation, db, EventState, Overlap
from tt_calendar import utils
from sqlalchemy import false, true

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
            Reservation.query.filter_by(event_id=new_event.id).delete() # uneecessary?
            self.create_reservations(user, new_event, form_data['table_ids'])

            db.session.commit()

            self.event_state_handler(new_event)

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

            db.session.commit()

            self.event_state_handler(event)

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


    def delete_event(self, event):
        """
        Delete the event from the database.
        """
        try:
            event.deleted = True
            db.session.commit()
            print(f"Event {event.id} successfully deleted.")
            self.event_state_handler(event)

        except Exception as e:
            db.session.rollback()
            print(f"Error deleting event {event.id}: {e}")
            raise


    # =====================================
    #      Event State Checker Routine
    # =====================================


    def event_state_handler(self, event):
        """
        Check and update event states and determine necessary actions.
        This get's triggered by creating, editing, deleting and event or a discord interaction.
        """
        try:
            followup_events = event.get_all_overlapping_events()

            print("Running the event state handler")
            print("Trying to update event state size")
            self.update_event_state_size(event)
            print("Trying to update event state overlap")
            self.update_event_state_overlap(event)
            print("Trying to handle event states and resolve")
            self.handle_event_states(event)


            for evt in followup_events:
                print("Running the event state handler")
                print("Trying to update event state size")
                self.update_event_state_size(evt)
                print("Trying to update event state overlap")
                self.update_event_state_overlap(evt)
                print("Trying to handle event states and resolve")
                self.handle_event_states(evt)

        except Exception as e:
            print(f"Error in eventstatechecker: {e}")
            raise


    def update_event_state_size(self, event):
        """
        Check size, if not checked before. Opens a chat in Discord
        """
        # Update state_size based on reservation size logic
        match event.state_size:
            case EventState.NOT_SET:                        # If not yet set, check for size
                if len(event.reservations) >= 4:
                    event.state_size = EventState.REQUESTED  # Needs approval by Vorstand
                    # TODO self.discord_handler.create_size_request(event)
                    db.session.commit()

            case EventState.REQUESTED:                      # If requested, but now smaller, reset
                if len(event.reservations) < 4:
                    event.state_size = EventState.NOT_SET  # Needs approval by Vorstand
                    # TODO self.discord_handler.cancel_size_request(event)
                    db.session.commit()
            case _:
                pass


    def update_event_state_overlap(self, event):
        """
        Check Overlaps. Opens Chat in Discord
        """
        current_overlapped_events = Overlap.query.filter_by(requesting_event_id=event.id).all()
        current_overlaps = {o.existing_event_id: o for o in current_overlapped_events}

        all_overlapping_events = self.get_overlapping_events(event)
        all_overlapping_event_ids = {oevent.id for oevent in all_overlapping_events}

        print(f"- - removing overlaps:")
        # Remove overlaps that no longer exist
        for overlap_id, overlap in current_overlaps.items():
            if overlap_id not in all_overlapping_event_ids:
                # The overlap is no longer valid, remove it
                db.session.delete(overlap)
                print(f"{overlap.id}")
                # TODO self.discord_handler.cancel_overlap_chat(event, overlap.existing_event)  # New method to cancel chat
                db.session.commit()


        print("- - adding new overlaps:")
        # Add new overlaps
        for oevent in all_overlapping_events:
            if oevent.id not in current_overlaps:
                # New overlap detected, add to database and request approval
                overlap = event.add_overlap(oevent)
                # TODO self.discord_handler.create_overlap_request(event, oevent) done?

                channel_id = self.discord_handler.open_ticket_for_overlap(
                    creator_id=event.user.discord_id,
                    overlapped_user_id=oevent.user.discord_id
                )

                overlap.request_discord_channel_id = channel_id
                print(f"{overlap.id} triggered a new channel")
                db.session.commit()

        

        pending_overlaps = event.get_pending_overlaps()
        denied_overlaps = event.get_denied_overlaps()

        if not pending_overlaps:
            if denied_overlaps:
                event.state_overlap = EventState.DENIED     # At least one was denied
            else:
                event.state_overlap = EventState.NOT_SET    # All overlaps have been taken back.
        else:
            event.state_overlap = EventState.REQUESTED      # Needs resolution
        db.session.commit()


    def handle_event_states(self, event):
        # First check for Denial
        if event.state_size == EventState.DENIED or event.state_overlap == EventState.DENIED:
            event.deleted = True
            # TODO self.discord_handler.cancel_size_request(event)
            # TODO self.discord_handler.cancel_overlap_requests(event)
            db.session.commit()
            return

        # Do nothing if still pending requests
        if (event.state_size == EventState.REQUESTED or \
            event.state_overlap == EventState.REQUESTED):   # If either is still in Request
            return

        # If this is reached, it must be Not Set and Approved only!
        if event.is_published:
            return
        
        event.set_publish_state()       # Sets to published
        message_id = self.discord_handler.post_to_discord(event, action="update")
        if message_id:
            event.discord_post_id = message_id
        

        # Delete those that the new event overlaps.
        approved_overlaps = Overlap.query.filter_by(existing_event_id=event.id, state=EventState.APPROVED).all()

        for overlap in approved_overlaps:
            requesting_event = overlap.requesting_event
            db.session.delete(requesting_event)  # Delete other event
            # TODO self.discord_handler.cancel_overlap_chat(event, requesting_event)  # Notify Discord
            db.session.delete(overlap)  # Remove overlap record

        db.session.commit()


    def get_overlapping_events(self, event):
        """
        Find overlapping events based on time and table reservations.
        """
        overlapping_events = Event.get_regular_events().filter(
            Event.id != event.id,
            Event.deleted == False,
            Event.start_time < event.end_time,
            Event.end_time > event.start_time,
            Event.reservations.any(Reservation.table_id.in_(
                [r.table_id for r in event.reservations]
            ))
        ).all()
        return overlapping_events
