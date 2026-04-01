from classes.IMessage import IMessage
from datetime import datetime


class IMediaMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, url: str):
        super().__init__(id, sender_id, "media", timestamp)
        self.url = url

    def print(self) -> str:
        return f"Media URL: {self.url}"
