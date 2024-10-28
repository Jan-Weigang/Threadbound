from functools import wraps
from flask import redirect, url_for, session
from flask_dance.contrib.discord import discord  # Assuming you're using Flask-Dance for Discord OAuth

# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not discord.authorized:
#             return redirect(url_for('discord.login'))
#         return f(*args, **kwargs)
#     return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not discord.authorized or not session.get('is_club_member', False):
            return redirect(url_for('discord.login'))
        return f(*args, **kwargs)
    return decorated_function