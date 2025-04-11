import os, json

from dotenv import load_dotenv
load_dotenv()

# ======================================
# ============= Variables ==============
# ======================================

# Getting the TOKEN from ENV - Bot will not work without it.
discord_token_str = os.getenv('DISCORD_TOKEN')
if not discord_token_str or not isinstance(discord_token_str, str):
    raise EnvironmentError("DISCORD_TOKEN must be a non-empty string")

discord_token = str(discord_token_str)


# Parsing CHANNELS as JSON from ENV
kalender_channels_json = os.getenv('CHANNELS')
if not kalender_channels_json:
    raise EnvironmentError("CHANNELS must be defined and cannot be empty")
try:
    kalender_channels = json.loads(kalender_channels_json)
except json.JSONDecodeError:
    raise ValueError("CHANNELS must be valid JSON")


# Validating necessary intergers from ENV
guild_id_str = os.getenv('GUILD_ID')
if not guild_id_str or not guild_id_str.isdigit():
    raise ValueError("GUILD_ID must be a valid integer")
guild_id = int(guild_id_str)


raw_guild_roles = {
    "bot": os.getenv('BOT_ROLE_ID'),
    "member": os.getenv('MEMBER_ROLE_ID'),
    "beirat": os.getenv('BEIRAT_ROLE_ID'),
    "vorstand": os.getenv('VORSTAND_ROLE_ID'),
    "mod": os.getenv('MOD_ROLE_ID'),
    "admin": os.getenv('ADMIN_ROLE_ID')
}
guild_roles = {}

for role_name, role_id_str in raw_guild_roles.items():
    if not role_id_str or not role_id_str.isdigit():
        raise ValueError(f"{role_name.upper()}_ROLE_ID must be a valid integer")

    guild_roles[role_name] = int(role_id_str)


ticket_category_id: int = int(os.getenv('TICKET_CATEGORY_ID')) # type: ignore
ticket_log_id: int = int(os.getenv('TICKET_LOG_ID')) # type: ignore

