from classes.IMessage import IMessage
from datetime import datetime


class IStoryShareMessage(IMessage):
    def __init__(self, id: int, sender_id: int, timestamp: datetime, story_author_username: str | None, story_caption: str | None, story_url: str | None):
        super().__init__(id, sender_id, "story_share", timestamp)
        self.story_author_username = story_author_username
        self.story_caption = story_caption
        self.story_url = story_url

    def print(self) -> str:
        if self.story_author_username is None or self.story_caption is None or self.story_url is None:
            return f"Unavailable Story Share"

        return f"Story from {self.story_author_username} with caption \"{self.story_caption}\" -> {self.story_url}"
