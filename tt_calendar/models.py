from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import TypeDecorator, DateTime
from datetime import datetime
from nanoid import generate
from sqlalchemy import Column, String
import pytz

from enum import Enum
from sqlalchemy import Enum as SQLAEnum
from sqlalchemy.exc import IntegrityError

# ============================================================================
#                            Database Structure 
# ============================================================================
    

# ===================================================
#                       Init
# ===================================================

# Initialize SQLAlchemy
db = SQLAlchemy()

# ===================================================
#              Query &  Helper Classes
# ===================================================


class EventState(Enum):
    NOT_SET = "Not Set"
    REQUESTED = "Requested"
    APPROVED = "Approved"
    DENIED = "Denied"


event_attendees = db.Table('event_attendees',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


event_overlaps = db.Table(
    "event_overlaps",
    db.Column("event_id", db.String(21), db.ForeignKey("event.id"), primary_key=True),  # The "owner" of the overlap
    db.Column("overlapping_event_id", db.String(21), db.ForeignKey("event.id"), primary_key=True)  # The allowed overlap
)


class AwareDateTime(TypeDecorator):
    """Results returned as aware datetimes, not naive ones."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                raise ValueError("Cannot store naive datetime")
            # Convert to UTC before storing
            utc_value = value.astimezone(pytz.utc)
            return utc_value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            # Convert UTC to Berlin time when retrieving
            return value.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Berlin'))
        return value


# ===================================================
#                      Mixins
# ===================================================


from sqlalchemy import Boolean, select, false

class SoftDeleteMixin:
    """Mixin to add soft delete functionality."""
    deleted = db.Column(Boolean, default=False, nullable=False)

    @classmethod
    def active(cls):
        """Return only non-deleted records using SQLAlchemy 2.0 syntax."""
        return db.session.query(cls).filter(cls.deleted == false())

# ===================================================
#                        Models
# ===================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)

class EventType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    events = db.relationship('Event', backref='event_type', lazy=True)
    color = db.Column(db.String(7), nullable=False)
    should_not_post_to_discord = db.Column(db.Boolean, nullable=False, default=False)


class Publicity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    events = db.relationship('Event', backref='publicity', lazy=True)
    should_not_post_to_discord = db.Column(db.Boolean, nullable=False, default=False)

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

class GameCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.Text, nullable=False)
    events = db.relationship('Event', backref='game_category', lazy=True)
    
    # Foreign key to DiscordChannel
    discord_channel_id = db.Column(db.BigInteger, db.ForeignKey('discord_channel.id'), nullable=True)
    channel = db.relationship('DiscordChannel', back_populates='game_categories')

    @property
    def channel_name(self):
        return self.channel.name if self.channel else "No Channel Assigned"

class DiscordChannel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_channel_id = db.Column(db.BigInteger, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    server = db.relationship('Server', back_populates='channels')

    # One-to-many relationship with GameCategory
    game_categories = db.relationship('GameCategory', back_populates='channel', lazy=True)
    

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_server_id = db.Column(db.BigInteger, unique=True, nullable=False)  # Discord server (guild) ID
    name = db.Column(db.String(100), nullable=False)

    # One-to-many relationship with DiscordChannel
    channels = db.relationship('DiscordChannel', back_populates='server', lazy=True)


# Event Model
class Event(db.Model, SoftDeleteMixin):
    __tablename__ = "event"
    id = Column(String(21), primary_key=True, default=lambda: generate(size=12))

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    discord_post_id = db.Column(db.String(255), nullable=True)
    attend_self = db.Column(db.Boolean, nullable=False, default=False)

    # Templating
    is_template = db.Column(db.Boolean, nullable=False, default=False)
    template_id = db.Column(db.String(21), db.ForeignKey('event.id'), nullable=True)  # Self-referential FK
    template = db.relationship('Event', remote_side=[id], backref='instances')

    # Recurring Events
    recurrence_rule = db.Column(db.Text, nullable=True)  # Store RRULE string for ICS compatibility
    excluded_dates = db.Column(db.Text, nullable=True, default="")  # newline-separated ISO dates
    
    # Datetime
    time_created = db.Column(AwareDateTime(), nullable=False, default=lambda: datetime.now(pytz.utc))
    time_updated = db.Column(AwareDateTime(), nullable=True, onupdate=lambda: datetime.now(pytz.utc))
    start_time = db.Column(AwareDateTime(), nullable=False)
    end_time = db.Column(AwareDateTime(), nullable=False)

    # Forein Keys
    game_category_id = db.Column(db.Integer, db.ForeignKey('game_category.id'), nullable=False)
    event_type_id = db.Column(db.Integer, db.ForeignKey('event_type.id'), nullable=False)
    publicity_id = db.Column(db.Integer, db.ForeignKey('publicity.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    reservations = db.relationship('Reservation', backref='associated_event', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='events')
    attendees = db.relationship('User', secondary=event_attendees, backref='attending_events')

    # States
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    state_size = db.Column(SQLAEnum(EventState), nullable=False, default=EventState.NOT_SET)
    size_request_discord_channel_id = db.Column(db.BigInteger, unique=True, nullable=True)
    state_overlap = db.Column(SQLAEnum(EventState), nullable=False, default=EventState.NOT_SET)

    def __repr__(self):
        return f"<Event '{self.name}' from {self.start_time} to {self.end_time}>"

    @property
    def duration(self):
        return self.end_time - self.start_time

    @classmethod
    def get_regular_events(cls):
        return cls.query.filter_by(is_template=False, deleted=False)
    
    @classmethod
    def get_active_events(cls):
        return cls.query.filter_by(deleted=False)
    
    @classmethod
    def get_template_events(cls):
        return cls.query.filter_by(is_template=True, deleted=False)
    
    def get_discord_message_url(self):
        if self.discord_post_id and self.game_category and self.game_category.channel: # type: ignore
            server_id = self.game_category.channel.server.discord_server_id # type: ignore
            channel_id = self.game_category.channel.discord_channel_id # type: ignore
            return f"discord.com/channels/{server_id}/{channel_id}/{self.discord_post_id}"
        return None


    def add_overlap(self, existing_event):
        """Add an overlap request."""
        overlap = Overlap(
            requesting_event_id=self.id,            # type: ignore
            existing_event_id=existing_event.id,    # type: ignore
            state=EventState.REQUESTED              # type: ignore
        )
        db.session.add(overlap)
        db.session.commit()
        return overlap


    def get_pending_overlaps(self):
        """Return all overlaps with a 'REQUESTED' state."""
        return Overlap.query.filter_by(
            requesting_event_id=self.id,
            state=EventState.REQUESTED
        ).all()
    

    def get_denied_overlaps(self):
        """Return all overlaps with a 'REQUESTED' state."""
        return Overlap.query.filter_by(
            requesting_event_id=self.id,
            state=EventState.DENIED
        ).all()
    

    def get_all_overlapping_events(self):
        """
        Retrieve all events that overlap with this one, both as requester and as existing event.
        Excludes deleted events.
        """
        # Events that this event is overlapping (outgoing overlaps)
        outgoing_overlaps = Overlap.query.filter_by(requesting_event_id=self.id).all()
        outgoing_events = [overlap.existing_event for overlap in outgoing_overlaps if not overlap.existing_event.deleted]

        # Events that are overlapping this event (incoming overlaps)
        incoming_overlaps = Overlap.query.filter_by(existing_event_id=self.id).all()
        incoming_events = [overlap.requesting_event for overlap in incoming_overlaps if not overlap.existing_event.deleted]

        # Combine both lists (ensuring uniqueness)
        return set(outgoing_events + incoming_events)

    

    # Update the method for publication
    def set_publish_state(self):
        """Set the event as published if approved."""
        if (self.state_size == EventState.APPROVED or self.state_size == EventState.NOT_SET) and \
           (self.state_overlap == EventState.APPROVED or self.state_overlap == EventState.NOT_SET):
            self.is_published = True
            db.session.commit()
        else:
            self.is_published = False
            db.session.commit()
    


# Reservation Model
class Reservation(db.Model):
    id = Column(String(21), primary_key=True, default=lambda: generate(size=12))

    # Templating
    is_template = db.Column(db.Boolean, default=False, nullable=False)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.String(21), db.ForeignKey('event.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('table.id'), nullable=False)

    # Relationships
    user = db.relationship('User', backref='reservations')
    table = db.relationship('Table', backref='reservations')

    def __repr__(self):
        return f"<Reservation for table {self.table_id} at {self.associated_event.start_time}>" # type: ignore
    

    @classmethod
    def get_regular_reservations(cls):
        return cls.query.join(Event).filter(cls.is_template==False, Event.deleted==False)
    
    @classmethod
    def get_template_reservations(cls):
        return cls.query.join(Event).filter(cls.is_template==True, Event.deleted==False)
    
    @classmethod
    def get_template_children(cls):
        return cls.query.join(Event).filter(cls.is_template==False, Event.deleted==False, Event.template_id.isnot(None))
    


class Overlap(db.Model):
    id = Column(String(21), primary_key=True, default=lambda: generate(size=12))
    request_discord_channel_id = db.Column(db.BigInteger, unique=True, nullable=True)
    
    # Foreign Keys for the events involved in the overlap
    requesting_event_id = db.Column(db.String(21), db.ForeignKey('event.id'), nullable=False)
    existing_event_id = db.Column(db.String(21), db.ForeignKey('event.id'), nullable=False)
    
    # Relationship to the Event model
    requesting_event = db.relationship('Event', foreign_keys=[requesting_event_id], backref='requested_overlaps')
    existing_event = db.relationship('Event', foreign_keys=[existing_event_id], backref='existing_overlaps')

    # State of the overlap request
    state = db.Column(SQLAEnum(EventState), nullable=False, default=EventState.NOT_SET)

    # Metadata
    created_at = db.Column(AwareDateTime(), nullable=False, default=lambda: datetime.now(pytz.utc))
    updated_at = db.Column(AwareDateTime(), nullable=True, onupdate=lambda: datetime.now(pytz.utc))


    def resolve_overlap(self, new_state):
        """Update the state of a specific overlap."""
        self.state = new_state
        db.session.commit()