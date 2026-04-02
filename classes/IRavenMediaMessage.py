from classes.IMessage import IMessage
from classes.IMediaType import IMediaType
from datetime import datetime


class IRavenMediaMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, type: IMediaType, expires_at: datetime, url: str):
        super().__init__(id, sender_id, "raven_media", timestamp)
        self.type = type
        self.expires_at = expires_at
        self.url = url

    def print(self) -> str:
        if self.expires_at < datetime.now():
            return f"Temporary {self.type.print()} -> Expired at {self.expires_at.strftime('%d/%m/%Y @ %H:%M:%S')}"

        return f"Temporary {self.type.print()} -> {self.url} (Expires at {self.expires_at.strftime('%d/%m/%Y @ %H:%M:%S')})"
