from datetime import datetime

from classes.IMediaType import IMediaType


class IMessage:
    def __init__(self, id: int, sender_id: int, type: str, timestamp: datetime):
        self.id = id
        self.sender_id = sender_id
        self.type = type
        self.timestamp = timestamp

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls.print is IMessage.print:
            raise TypeError(f"{cls.__name__} must override print()")

    def __eq__(self, other):
        return self.id == other.id

    def print(self) -> str:
        return f"[{self.type}] {self.id}"

    @classmethod
    def from_json(cls, json_data: dict):
        match json_data["item_type"]:
            case "text":
                from classes.ITextMessage import ITextMessage

                return ITextMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    json_data["text"]
                )

            case "clip":
                from classes.IClipMessage import IClipMessage

                clip_data: dict = json_data["clip"]["clip"]
                return IClipMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    clip_data["user"]["username"],
                    clip_data["caption"]["text"] if hasattr(clip_data, "caption") else None,
                    clip_data["video_versions"][0]["url"]
                )

            case "story_share":
                from classes.IStoryShareMessage import IStoryShareMessage

                story_data: dict | None = None
                try:
                    story_data: dict = json_data["story_share"]["media"]
                except KeyError:
                    pass

                return IStoryShareMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    story_data["user"]["username"] if story_data is not None and hasattr(story_data, "user") else None,
                    story_data["caption"]["text"] if story_data is not None and hasattr(story_data, "caption") else None,
                    story_data["video_versions"][0]["url"] if story_data is not None and hasattr(story_data, "video_versions") else None
                )

            case "media_share":
                from classes.IMediaShareMessage import IMediaShareMessage

                media_data: dict = json_data["direct_media_share"]["media"]
                return IMediaShareMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    media_data["user"]["username"] if hasattr(media_data, "user") else None,
                    media_data["image_versions2"]["candidates"][0]["url"]
                )

            case "raven_media":  # Temporary media
                from classes.IRavenMediaMessage import IRavenMediaMessage

                media_data: dict = json_data["raven_media"]
                return IRavenMediaMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    IMediaType.from_number(int(media_data["media_type"])),
                    datetime.fromtimestamp(int(media_data["url_expire_at_secs"]) if media_data["url_expire_at_secs"] is not None else 0),
                    media_data.get("image_versions2", {}).get("candidates", [{}])[0].get("url") if media_data["media_type"] == 1 else media_data.get("video_versions", [{}])[0].get("url")
                )

            case "media":  # Permanent media
                from classes.IMediaMessage import IMediaMessage

                media_data: dict = json_data["media"]
                return IMediaMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    IMediaType.from_number(int(media_data["media_type"])),
                    media_data["image_versions2"]["candidates"][0]["url"] if media_data["media_type"] == 1 else media_data["video_versions"][0]["url"]
                )

            case "voice_media":
                from classes.IVoiceMessage import IVoiceMessage

                voice_data: dict = json_data["voice_media"]["media"]
                return IVoiceMessage(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000),  # Instagram timestamps are in MICROSECONDS (no idea why)
                    voice_data["audio"]["audio_src"]
                )

            case _:
                return cls(
                    int(json_data["item_id"]),
                    int(json_data["user_id"]),
                    json_data["item_type"],
                    datetime.fromtimestamp(int(json_data["timestamp"]) / 1000000)  # Instagram timestamps are in MICROSECONDS (no idea why)
                )
