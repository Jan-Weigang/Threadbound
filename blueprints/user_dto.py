from dataclasses import dataclass


@dataclass
class UserDto:
    name: str | None
    id: str | int | None

    is_member: bool
    is_beirat: bool
    is_vorstand: bool
    is_admin: bool

    def __post_init__(self):
        # Apply hierarchy
        self.is_vorstand = self.is_vorstand or self.is_admin
        self.is_beirat = self.is_beirat or self.is_vorstand
        self.is_member = self.is_member or self.is_beirat

    @property
    def member(self) -> str:
        return "Ja" if self.is_member else "Nein"

    @property
    def beirat(self) -> str:
        return "Ja" if self.is_beirat else "Nein"

    @property
    def vorstand(self) -> str:
        return "Ja" if self.is_vorstand else "Nein"

    @property
    def admin(self) -> str:
        return "Ja" if self.is_admin else "Nein"

    def __getitem__(self, key):
        return getattr(self, key)

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "is_member": self.is_member,
            "is_beirat": self.is_beirat,
            "is_vorstand": self.is_vorstand,
            "is_admin": self.is_admin,
        }

    @classmethod
    def from_session(cls, session):
        return cls(
            name=session.get("username"),
            id=session.get("user_id"),
            is_member=bool(session.get("is_member")),
            is_beirat=bool(session.get("is_beirat")),
            is_vorstand=bool(session.get("is_vorstand")),
            is_admin=bool(session.get("is_admin")),
        )