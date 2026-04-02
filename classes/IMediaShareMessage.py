from classes.IMessage import IMessage
from datetime import datetime


class IMediaShareMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, author_username: str, image_url: str):
        super().__init__(id, sender_id, "media_share", timestamp)
        self.author_username = author_username
        self.image_url = image_url

    def print(self) -> str:
        return f"Media share from \"{self.author_username}\" -> {self.image_url}"
