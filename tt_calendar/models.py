from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import TypeDecorator, DateTime
from datetime import datetime
from nanoid import generate
from sqlalchemy import Column, String
import pytz

from sqlalchemy.orm import class_mapper

# ======================================
# ========= Database Structure =========
# ======================================
    

# Initialize SQLAlchemy
db = SQLAlchemy()

event_attendees = db.Table('event_attendees',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
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



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(100), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)

class EventType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    events = db.relationship('Event', backref='event_type', lazy=True)
    color = db.Column(db.String(7), nullable=False) 

class Publicity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    events = db.relationship('Event', backref='publicity', lazy=True)

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
class Event(db.Model):
    id = Column(String(21), primary_key=True, default=lambda: generate(size=12))

    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    discord_post_id = db.Column(db.String(255), nullable=True)

    # Templating
    is_template = db.Column(db.Boolean, nullable=False, default=False) 
    recurring_cycle = db.Column(db.String(10), nullable=True)  # 'day', 'week', or 'month'
    recurring_interval = db.Column(db.Integer, nullable=True)
    
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

    @classmethod
    def get_regular_events(cls):
        return cls.query.filter_by(is_template=False)
    
    @classmethod
    def get_template_events(cls):
        return cls.query.filter_by(is_template=True)
    
    def get_discord_message_url(self):
        if self.discord_post_id and self.game_category and self.game_category.channel: # type: ignore
            server_id = self.game_category.channel.server.discord_server_id # type: ignore
            channel_id = self.game_category.channel.discord_channel_id # type: ignore
            return f"discord.com/channels/{server_id}/{channel_id}/{self.discord_post_id}"
        return None

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
    

    @classmethod
    def get_regular_reservations(cls):
        return cls.query.filter_by(is_template=False)
    
    @classmethod
    def get_template_reservations(cls):
        return cls.query.filter_by(is_template=True)
    

