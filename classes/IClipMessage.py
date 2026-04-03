from classes.IMessage import IMessage
from datetime import datetime


class IClipMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, clip_sender_username: str, clip_caption: str | None, clip_url: str):
        super().__init__(id, sender_id, "clip", timestamp)
        self.clip_sender_username = clip_sender_username
        self.clip_caption = clip_caption
        self.clip_url = clip_url

    def print(self) -> str:
        return f"Clip from {self.clip_sender_username} {f"titled \"{self.clip_caption}\"" if self.clip_caption is not None else ""} -> {self.clip_url}"
