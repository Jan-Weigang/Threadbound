from tt_calendar.models import User, db


class UserManager:
    def __init__(self, discord_handler, discord_api):
        self.discord_handler = discord_handler
        self.discord_api = discord_api

    def save_or_update_user(self, discord_id, new_username):
        user = User.query.filter_by(discord_id=discord_id).first()
        
        if user:
            if user.username != new_username:
                user.username = new_username
                db.session.commit()
                print(f"Updated nickname for user {discord_id}: {new_username}")
        else:
            user = User(discord_id=discord_id, username=new_username)  # type: ignore
            db.session.add(user)
            db.session.commit()
            print(f"Added new user {discord_id} with username: {new_username}")
        return user


    def get_or_create_user(self):
        resp = self.discord_api.get('/api/users/@me')
        assert resp.ok, resp.text
        user_info = resp.json()

        discord_id = user_info['id']
        nickname = self.discord_handler.get_nickname(discord_id)
        username = nickname or user_info['username']

        user = User.query.filter_by(discord_id=discord_id).first()
        if not user:
            user = User(discord_id=discord_id, username=username)  # type: ignore
            db.session.add(user)
            db.session.commit()
        return user
