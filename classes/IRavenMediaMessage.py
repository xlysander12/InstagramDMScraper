from classes.IMessage import IMessage
from datetime import datetime


class IRavenMediaMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, expires_at: datetime, url: str):
        super().__init__(id, sender_id, "raven_media", timestamp)
        self.expires_at = expires_at
        self.url = url

    def print(self) -> str:
        if self.expires_at < datetime.now():
            return f"Temporary photo -> Expired at {self.expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

        return f"Temporary photo -> {self.url} (Expires at {self.expires_at.strftime('%Y-%m-%d %H:%M:%S')})"
