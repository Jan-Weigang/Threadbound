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


# Validating necessary intergers from ENV
guild_id_str = os.getenv('GUILD_ID')
if not guild_id_str or not guild_id_str.isdigit():
    raise ValueError("GUILD_ID must be a valid integer")
guild_id = int(guild_id_str)


def parse_role_ids(value: str, role_name: str) -> list[int]:
    if not value:
        raise ValueError(f"{role_name.upper()}_ROLE_ID is missing")

    ids = [v.strip() for v in value.split(',')]
    
    for v in ids:
        if not v.isdigit():
            raise ValueError(f"Invalid ID '{v}' in {role_name.upper()}_ROLE_ID — must be digits only.")

    return [int(v) for v in ids]


def parse_single_role_id(value: str, role_name: str) -> int:
    if not value or not value.strip().isdigit():
        raise ValueError(f"{role_name.upper()}_ROLE_ID must be a valid integer")
    return int(value.strip())



guild_roles = {
    "bot":      parse_single_role_id(os.getenv('BOT_ROLE_ID'), 'bot'),
    "member":   parse_role_ids(os.getenv('MEMBER_ROLE_ID'), 'member'),
    "beirat":   parse_role_ids(os.getenv('BEIRAT_ROLE_ID'), 'beirat'),
    "vorstand": parse_role_ids(os.getenv('VORSTAND_ROLE_ID'), 'vorstand'),
    "admin":    parse_role_ids(os.getenv('ADMIN_ROLE_ID'), 'admin')
}

ticket_category_id: int = int(os.getenv('TICKET_CATEGORY_ID')) # type: ignore
ticket_log_id: int = int(os.getenv('TICKET_LOG_ID')) # type: ignore

