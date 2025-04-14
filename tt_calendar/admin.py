from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from tt_calendar.models import db, User, EventType, Publicity, Table, GameCategory, DiscordChannel, Event, Overlap  # Adjust paths as needed

# Initialize Admin instance (assuming it will be used in app.py)
admin = Admin(name='TableTop Admin', template_mode='bootstrap4')


class UserView(ModelView):
    column_list = ('id', 'discord_id', 'username')
    form_columns = ('discord_id', 'username')

class EventTypeView(ModelView):
    column_list = ('id', 'name', 'color')
    form_columns = ('name', 'color')

class PublicityView(ModelView):
    column_list = ('id', 'name')
    form_columns = ('name',)

class TableView(ModelView):
    column_list = ('id', 'name', 'type', 'capacity')
    form_columns = ('name', 'type', 'capacity')

class GameCategoryView(ModelView):
    column_list = ('id', 'name', 'channel_name', 'icon')
    form_columns = ('name', 'icon', 'channel') 

class DiscordChannelView(ModelView):
    column_list = ('id', 'discord_channel_id', 'name')
    form_columns = ('discord_channel_id', 'name')

class EventView(ModelView):
#     column_list = ('id', 'name', 'game_category_id', 'event_type_id', 'publicity_id', 'user_id', 'discord_post_id')
#     form_columns = ('name', 'description', 'game_category', 'event_type', 'publicity', 'user_id', 'discord_post_id')

    column_list = ('id', 'name', 'game_category_id', 'event_type_id', 'publicity_id', 'user_id', 'discord_post_id', 'attendees', 'state_size', 'state_overlap', 'size_request_discord_channel_id', 'requested_overlaps', 'is_published', 'deleted', 'is_template', 'recurrence_rule')
    form_columns = ('name', 'description', 'game_category', 'event_type', 'publicity', 'user_id', 'discord_post_id', 'attendees', 'state_size', 'state_overlap', 'size_request_discord_channel_id', 'requested_overlaps', 'is_published', 'deleted', 'is_template', 'recurrence_rule')
    
    # Custom column formatting for attendees to display usernames instead of raw user objects
    column_formatters = {
        'attendees': lambda view, context, model, name: ', '.join([user.username for user in model.attendees])
    }
    # This will allow dropdowns for the foreign key fields
    form_args = {
        'game_category': {'query_factory': lambda: GameCategory.query.all()},
        'event_type': {'query_factory': lambda: EventType.query.all()},
        'publicity': {'query_factory': lambda: Publicity.query.all()},
        'user_id': {'query_factory': lambda: User.query.all()}
    }

class OverlapView(ModelView):
    column_list = ('id', 'request_discord_channel_id', 'display_name', 'state', 'created_at')
    form_columns = ('request_discord_channel_id', 'requesting_event', 'existing_event', 'state')

    column_labels = {
        'request_discord_channel_id': 'Discord Channel ID',
        'display_name': 'Involved Events',
        'state': 'Status',
        'created_at': 'Created'
    }

    column_formatters = {
        'display_name': lambda v, c, m, p: f"{m.requesting_event.name} ⟷ {m.existing_event.name}"
    }

    can_create = False
    can_edit = True
    can_delete = True


def init_admin(app):
    admin.init_app(app)
    admin.add_view(UserView(User, db.session))
    admin.add_view(EventTypeView(EventType, db.session))
    admin.add_view(PublicityView(Publicity, db.session))
    admin.add_view(TableView(Table, db.session))
    admin.add_view(GameCategoryView(GameCategory, db.session))
    admin.add_view(DiscordChannelView(DiscordChannel, db.session))
    admin.add_view(EventView(Event, db.session)) 
    admin.add_view(OverlapView(Overlap, db.session)) 