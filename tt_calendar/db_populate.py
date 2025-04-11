import os
import json
import base64
from .models import *
from flask import current_app as app

from dotenv import load_dotenv
load_dotenv()

def check_and_populate_db():
    with app.app_context():
        # Check if the GameCategory table is empty
        try:
            db.session.query(GameCategory).first()      
        except:
            reset_database()

def reset_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        add_initial_data()

def add_initial_data():
    add_game_categories()
    add_event_types()
    add_publicity_levels()
    add_tables()
    add_server_from_env()
    add_channels_from_env()

def add_game_categories():
    svg_pp = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"><polygon points="12,2 2,9 6,22 18,22 22,9" fill="#4f379e"/><text x="8" y="16" font-size="7" fill="#ffffff">20</text></svg>"""
    svg_boardgames = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><rect x="1" y="1" width="22" height="22" rx="3" fill="#d9cf68" /><circle cx="8" cy="8" r="2" fill="#000" /><circle cx="16" cy="8" r="2" fill="#000" /><circle cx="8" cy="16" r="2" fill="#000" /><circle cx="16" cy="16" r="2" fill="#000" /></svg>"""
    svg_tcg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="20" rx="2" fill="#ff6347" stroke="#000" /><rect x="6" y="2" width="16" height="20" rx="2" fill="#ffffff" stroke="#000" transform="rotate(10 12 12)"/></svg>"""
    svg_tt = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><!-- Main Body --><rect x="3" y="12" width="18" height="7" fill="#4caf50" /><!-- Turret --><rect x="6" y="7" width="12" height="5" fill="#388e3c" /><!-- Wheels --><circle cx="5" cy="19" r="2.5" fill="#000" /><circle cx="12" cy="19" r="2.5" fill="#000" /><circle cx="19" cy="19" r="2.5" fill="#000" /><!-- Gun Barrel --><rect x="16" y="5.5" width="7" height="2.5" fill="#000" /></svg>"""

    encoded_svgs = [
        ("Pen & Paper", base64.b64encode(svg_pp.encode('utf-8')).decode('utf-8')),
        ("Brettspiele", base64.b64encode(svg_boardgames.encode('utf-8')).decode('utf-8')),
        ("Trading Card Games", base64.b64encode(svg_tcg.encode('utf-8')).decode('utf-8')),
        ("Tabletop Wargames", base64.b64encode(svg_tt.encode('utf-8')).decode('utf-8')),
    ]
    categories = [GameCategory(name=name, icon=icon) for name, icon in encoded_svgs] # type: ignore
    db.session.bulk_save_objects(categories)
    db.session.commit()

def add_event_types():
    event_types = [
        EventType(name="Spieltermin", color="#ADD8E6"), # type: ignore
        EventType(name="Stammtisch", color="#a3c999"), # type: ignore
        EventType(name="Kampagne", color="#be91e3"), # type: ignore
        EventType(name="Turnier", color="#e38190"), # type: ignore
        EventType(name="Vereinsevent", color="#c7c993") # type: ignore
    ]
    db.session.bulk_save_objects(event_types)
    db.session.commit()

def add_publicity_levels():
    publicity_levels = [
        Publicity(name="Geschlossene Gruppe"), # type: ignore
        Publicity(name="Vereinsintern"), # type: ignore
        Publicity(name="Öffentlich") # type: ignore
    ]
    db.session.bulk_save_objects(publicity_levels)
    db.session.commit()

def add_tables():
    tables = [
        Table(id=1, type="RPG", name="Tisch 1", capacity=6), # type: ignore
        Table(id=2, type="TT", name="Tisch 2", capacity=6), # type: ignore
        Table(id=3, type="TT", name="Tisch 3", capacity=6), # type: ignore
        Table(id=4, type="TT", name="Tisch 4", capacity=6), # type: ignore
        Table(id=5, type="TT", name="Tisch 5", capacity=6), # type: ignore
        Table(id=6, type="Halb", name="Tisch 6.1", capacity=4), # type: ignore
        Table(id=7, type="Halb", name="Tisch 6.2", capacity=4), # type: ignore
        Table(id=8, type="RPG", name="Tisch 7", capacity=6), # type: ignore
        Table(id=9, type="Halb", name="Tisch 7.5", capacity=4) # type: ignore
    ]
    db.session.bulk_save_objects(tables)
    db.session.commit()


def add_channels_from_env():
    channels_json = os.getenv('CHANNELS')
    if not channels_json:
        print("No discord channels found in environment.")
        return

    try:
        channels_dict = json.loads(channels_json)
    except json.JSONDecodeError as e:
        print("Error parsing channels JSON:", e)
        return

    for name, discord_channel_id in channels_dict.items():
        if not DiscordChannel.query.filter_by(discord_channel_id=discord_channel_id).first():
            new_channel = DiscordChannel(discord_channel_id=discord_channel_id, name=name, server_id=1) # type: ignore
            db.session.add(new_channel)
            print(f"Added channel: {name} with ID {discord_channel_id}")
    db.session.commit()
    print("Channels added successfully.")


def add_server_from_env():
    # Fetch the server ID and name from environment variables
    discord_server_id = os.getenv('GUILD_ID')
    server_name = os.getenv('SERVER_NAME')

    # Ensure that necessary environment variables are set
    if not discord_server_id or not server_name:
        print("Error: GUILD_ID and SERVER_NAME must be set in environment variables.")
        return

    # Check if the server already exists in the database
    existing_server = Server.query.filter_by(discord_server_id=discord_server_id).first() # type: ignore
    if existing_server:
        print(f"Server '{server_name}' with ID '{discord_server_id}' already exists.")
        return

    # Create a new server entry
    new_server = Server(discord_server_id=discord_server_id, name=server_name) # type: ignore
    db.session.add(new_server)
    db.session.commit()
    print(f"Added server '{server_name}' with ID '{discord_server_id}' to the database.")



# def check_and_populate_db():
#     with app.app_context():
#         # Check if the GameCategory table is empty
#         try:
#             db.session.query(GameCategory).first()
#         except:
#             reset_database()


# def reset_database():
#     with app.app_context():
#         db.drop_all()
#         db.create_all()



#     def add_game_categories():
#         svg_pp = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"><polygon points="12,2 2,9 6,22 18,22 22,9" fill="#4f379e"/><text x="8" y="16" font-size="7" fill="#ffffff">20</text></svg>"""
#         svg_boardgames = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><rect x="1" y="1" width="22" height="22" rx="3" fill="#d9cf68" /><circle cx="8" cy="8" r="2" fill="#000" /><circle cx="16" cy="8" r="2" fill="#000" /><circle cx="8" cy="16" r="2" fill="#000" /><circle cx="16" cy="16" r="2" fill="#000" /></svg>"""
#         svg_tcg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="20" rx="2" fill="#ff6347" stroke="#000" /><rect x="6" y="2" width="16" height="20" rx="2" fill="#ffffff" stroke="#000" transform="rotate(10 12 12)"/></svg>"""
#         svg_tt = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><!-- Main Body --><rect x="3" y="12" width="18" height="7" fill="#4caf50" /><!-- Turret --><rect x="6" y="7" width="12" height="5" fill="#388e3c" /><!-- Wheels --><circle cx="5" cy="19" r="2.5" fill="#000" /><circle cx="12" cy="19" r="2.5" fill="#000" /><circle cx="19" cy="19" r="2.5" fill="#000" /><!-- Gun Barrel --><rect x="16" y="5.5" width="7" height="2.5" fill="#000" /></svg>"""
        
#         encoded_svg_pp = base64.b64encode(svg_pp.encode('utf-8')).decode('utf-8')
#         encoded_svg_boardgames = base64.b64encode(svg_boardgames.encode('utf-8')).decode('utf-8')
#         encoded_svg_tcg = base64.b64encode(svg_tcg.encode('utf-8')).decode('utf-8')
#         encoded_svg_tt = base64.b64encode(svg_tt.encode('utf-8')).decode('utf-8')

#         categories = [
#             GameCategory(name="Pen & Paper", icon=encoded_svg_pp), # type: ignore
#             GameCategory(name="Brettspiele", icon=encoded_svg_boardgames), # type: ignore
#             GameCategory(name="Trading Card Games", icon=encoded_svg_tcg), # type: ignore
#             GameCategory(name="Tabletop Wargames", icon=encoded_svg_tt) # type: ignore
#         ]
#         db.session.bulk_save_objects(categories)
#         db.session.commit()

#     def add_event_types():
#         event_types = [
#             EventType(name="Spieltermin", color="#ADD8E6"), # type: ignore
#             EventType(name="Stammtisch", color="#a3c999"), # type: ignore
#             EventType(name="Kampagne", color="#be91e3"),  # type: ignore
#             EventType(name="Turnier", color="#e38190"), # type: ignore
#             EventType(name="Vereinsevent", color="#c7c993")  # type: ignore
#         ]
#         db.session.bulk_save_objects(event_types)
#         db.session.commit()


#     def add_publicity_levels():
#         publicity_levels = [
#             Publicity(name="Geschlossene Gruppe"), # type: ignore
#             Publicity(name="Offene Gruppe"),# type: ignore
#             Publicity(name="Öffentlich (Gäste)") # type: ignore
#         ]
#         db.session.bulk_save_objects(publicity_levels)
#         db.session.commit()

#     def add_tables():
#         tables = [
#             Table(id=1, type="RPG", name="Tisch 1", capacity=6), # type: ignore
#             Table(id=2, type="TT", name="Tisch 2", capacity=6), # type: ignore
#             Table(id=3, type="TT", name="Tisch 3", capacity=6), # type: ignore
#             Table(id=4, type="TT", name="Tisch 4", capacity=6), # type: ignore
#             Table(id=5, type="TT", name="Tisch 5", capacity=6), # type: ignore
#             Table(id=6, type="Halb", name="Tisch 6.1", capacity=4), # type: ignore
#             Table(id=7, type="Halb", name="Tisch 6.2", capacity=4), # type: ignore
#             Table(id=8, type="RPG", name="Tisch 7", capacity=6), # type: ignore
#             Table(id=9, type="Halb", name="Tisch 7.5", capacity=4) # type: ignore
#         ]
#         db.session.bulk_save_objects(tables)
#         db.session.commit()

#     def add_channels_from_env():
#         # Get JSON dict from the .env file
#         channels_json = os.getenv('CHANNELS')
#         if not channels_json:
#             print("No discord channels found in environment.")
#             return

#         try:
#             channels_dict = json.loads(channels_json)  # Parse JSON string to dict
#         except json.JSONDecodeError as e:
#             print("Error parsing channels JSON:", e)
#             return

#         # Add each channel to the database
#         for name, discord_channel_id in channels_dict.items():
#             # Check if the channel already exists to avoid duplicates
#             if not DiscordChannel.query.filter_by(discord_channel_id=discord_channel_id).first():
#                 new_channel = DiscordChannel(discord_channel_id=discord_channel_id, name=name) # type: ignore
#                 db.session.add(new_channel)
#                 print(f"Added channel: {name} with ID {discord_channel_id}")
#             else:
#                 print(f"Channel with ID {discord_channel_id} already exists; skipping.")
        
#         db.session.commit()  # Save all changes
#         print("Channels added successfully.")


#     # Populate initial data
#     with app.app_context():
#         add_game_categories()
#         add_event_types()
#         add_publicity_levels()
#         add_tables()
#         add_channels_from_env()
