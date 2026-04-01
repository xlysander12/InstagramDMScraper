from classes.IMessage import IMessage
from datetime import datetime


class ITextMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, text: str):
        super().__init__(id, sender_id, "text", timestamp)
        self.text = text

    def print(self) -> str:
        return self.text
