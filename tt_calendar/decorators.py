from functools import wraps
from flask import redirect, url_for, session, flash, request
from flask_dance.contrib.discord import discord  # Assuming you're using Flask-Dance for Discord OAuth

def require_min_role(min_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Login benötigt.", "warning")
                return redirect(url_for("cal_bp.view"))
        

            ROLE_ORDER = ['member', 'beirat', 'vorstand', 'admin']
            user_roles = [role for role in ROLE_ORDER if session.get(f'is_{role}')]
            if not user_roles:
                flash(f'Mindestens Rolle "<strong><i>{min_role.capitalize()}</i></strong>" benötigt! Du hast keine Rollen.', "danger")
                return redirect(url_for("cal_bp.view"))
                

            user_max_role = max(user_roles, key=ROLE_ORDER.index)
            if ROLE_ORDER.index(user_max_role) < ROLE_ORDER.index(min_role):
                flash(f'Mindestens Rolle "<strong><i>{min_role.capitalize()}</i></strong>" benötigt! Du bist nur <i>{user_max_role.capitalize()}</i>.', "danger")
                return redirect(url_for("cal_bp.view"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
